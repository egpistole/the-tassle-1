import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from datetime import datetime

from config import config
from models import db, User, GraduateProfile, PartyDetails, RegistryItem, ExternalRegistry
from forms import (
    RegistrationForm, LoginForm, ProfileEditForm, PartyDetailsForm,
    RegistryItemForm, ExternalRegistryForm, MarkPurchasedForm,
    SearchForm, AccountSettingsForm
)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please sign in to access that page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ─────────────────────────────────────────────
    # Context processors
    # ─────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow(),
            'search_form': SearchForm()
        }

    # ─────────────────────────────────────────────
    # Public routes
    # ─────────────────────────────────────────────

    @app.route('/')
    def index():
        # Get some recent public profiles for the homepage
        recent_profiles = GraduateProfile.query.filter_by(is_public=True)\
            .filter(GraduateProfile.first_name != '')\
            .order_by(GraduateProfile.updated_at.desc())\
            .limit(6).all()
        return render_template('index.html', recent_profiles=recent_profiles)

    @app.route('/search')
    def search():
        form = SearchForm(request.args)
        profiles = []
        searched = False

        query = request.args.get('query', '').strip()
        school = request.args.get('school', '').strip()
        year = request.args.get('year', '').strip()

        if query or school or year:
            searched = True
            q = GraduateProfile.query.filter_by(is_public=True)

            if query:
                search_term = f'%{query}%'
                q = q.filter(
                    or_(
                        GraduateProfile.first_name.ilike(search_term),
                        GraduateProfile.last_name.ilike(search_term),
                        GraduateProfile.school_name.ilike(search_term),
                        GraduateProfile.degree.ilike(search_term),
                    )
                )

            if school:
                q = q.filter(GraduateProfile.school_name.ilike(f'%{school}%'))

            if year:
                try:
                    year_int = int(year)
                    q = q.filter(GraduateProfile.graduation_year == year_int)
                except ValueError:
                    pass

            profiles = q.order_by(GraduateProfile.last_name).limit(50).all()

        return render_template('search.html', form=form, profiles=profiles, searched=searched)

    @app.route('/grad/<slug>')
    def public_profile(slug):
        profile = GraduateProfile.query.filter_by(slug=slug).first_or_404()
        if not profile.is_public and (not current_user.is_authenticated or current_user.id != profile.user_id):
            abort(404)

        registry_items = profile.registry_items.order_by(RegistryItem.is_purchased, RegistryItem.created_at).all()
        external_registries = profile.external_registries.all()
        mark_purchased_form = MarkPurchasedForm()

        return render_template(
            'profile_public.html',
            profile=profile,
            registry_items=registry_items,
            external_registries=external_registries,
            mark_purchased_form=mark_purchased_form
        )

    @app.route('/item/<int:item_id>/purchase', methods=['POST'])
    def mark_item_purchased(item_id):
        item = RegistryItem.query.get_or_404(item_id)
        form = MarkPurchasedForm()

        if form.validate_on_submit():
            if not item.is_fully_claimed:
                item.quantity_purchased = min(item.quantity_purchased + 1, item.quantity_needed)
                if item.quantity_purchased >= item.quantity_needed:
                    item.is_purchased = True
                if form.purchased_by_note.data:
                    item.purchased_by_note = form.purchased_by_note.data
                db.session.commit()
                flash(f'Thank you! "{item.title}" has been marked as purchased.', 'success')
            else:
                flash('This item has already been fully claimed.', 'warning')
        else:
            flash('Something went wrong. Please try again.', 'danger')

        return redirect(url_for('public_profile', slug=item.profile.slug))

    # ─────────────────────────────────────────────
    # Auth routes
    # ─────────────────────────────────────────────

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(email=form.email.data.lower().strip())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Get the user ID

            # Create empty profile
            profile = GraduateProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()

            login_user(user)
            flash('Welcome! Your account has been created. Let\'s set up your page.', 'success')
            return redirect(url_for('edit_profile'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Welcome back!', 'success')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid email or password. Please try again.', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been signed out.', 'info')
        return redirect(url_for('index'))

    # ─────────────────────────────────────────────
    # Authenticated routes
    # ─────────────────────────────────────────────

    @app.route('/dashboard')
    @login_required
    def dashboard():
        profile = current_user.profile
        registry_items = profile.registry_items.all() if profile else []
        external_registries = profile.external_registries.all() if profile else []
        return render_template(
            'dashboard.html',
            profile=profile,
            registry_items=registry_items,
            external_registries=external_registries
        )

    @app.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
    def edit_profile():
        profile = current_user.profile
        if not profile:
            profile = GraduateProfile(user_id=current_user.id)
            db.session.add(profile)
            db.session.commit()

        form = ProfileEditForm(obj=profile)

        if form.validate_on_submit():
            profile.first_name = form.first_name.data.strip()
            profile.last_name = form.last_name.data.strip()
            profile.photo_url = form.photo_url.data or None
            profile.personal_message = form.personal_message.data or None
            profile.school_name = form.school_name.data or None
            profile.degree = form.degree.data or None
            profile.graduation_date = form.graduation_date.data
            profile.is_public = form.is_public.data

            if form.graduation_date.data:
                profile.graduation_year = form.graduation_date.data.year

            # Generate/regenerate slug
            profile.generate_slug()

            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('profile_edit.html', form=form, profile=profile)

    @app.route('/party/edit', methods=['GET', 'POST'])
    @login_required
    def edit_party():
        profile = current_user.profile
        party = profile.party_details

        if not party:
            party = PartyDetails(profile_id=profile.id)
            db.session.add(party)
            db.session.commit()

        form = PartyDetailsForm(obj=party)

        if form.validate_on_submit():
            party.event_title = form.event_title.data or None
            party.event_date = form.event_date.data
            party.event_time = form.event_time.data or None
            party.location_name = form.location_name.data or None
            party.location_address = form.location_address.data or None
            party.rsvp_instructions = form.rsvp_instructions.data or None
            party.rsvp_deadline = form.rsvp_deadline.data
            party.additional_notes = form.additional_notes.data or None
            db.session.commit()
            flash('Party details have been saved!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('party_edit.html', form=form, profile=profile)

    @app.route('/registry/add', methods=['GET', 'POST'])
    @login_required
    def add_registry_item():
        profile = current_user.profile
        form = RegistryItemForm()

        if form.validate_on_submit():
            item = RegistryItem(
                profile_id=profile.id,
                title=form.title.data.strip(),
                description=form.description.data or None,
                price=form.price.data,
                quantity_needed=form.quantity_needed.data or 1,
                external_url=form.external_url.data or None,
                image_url=form.image_url.data or None,
                category=form.category.data or None,
                priority=form.priority.data
            )
            db.session.add(item)
            db.session.commit()
            flash(f'"{item.title}" has been added to your registry!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('registry_item_form.html', form=form, profile=profile, editing=False)

    @app.route('/registry/<int:item_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_registry_item(item_id):
        item = RegistryItem.query.get_or_404(item_id)
        if item.profile.user_id != current_user.id:
            abort(403)

        form = RegistryItemForm(obj=item)

        if form.validate_on_submit():
            item.title = form.title.data.strip()
            item.description = form.description.data or None
            item.price = form.price.data
            item.quantity_needed = form.quantity_needed.data or 1
            item.external_url = form.external_url.data or None
            item.image_url = form.image_url.data or None
            item.category = form.category.data or None
            item.priority = form.priority.data
            db.session.commit()
            flash(f'"{item.title}" has been updated!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('registry_item_form.html', form=form, profile=current_user.profile, editing=True, item=item)

    @app.route('/registry/<int:item_id>/delete', methods=['POST'])
    @login_required
    def delete_registry_item(item_id):
        item = RegistryItem.query.get_or_404(item_id)
        if item.profile.user_id != current_user.id:
            abort(403)
        title = item.title
        db.session.delete(item)
        db.session.commit()
        flash(f'"{title}" has been removed from your registry.', 'info')
        return redirect(url_for('dashboard'))

    @app.route('/external-registry/add', methods=['GET', 'POST'])
    @login_required
    def add_external_registry():
        profile = current_user.profile
        form = ExternalRegistryForm()

        if form.validate_on_submit():
            reg = ExternalRegistry(
                profile_id=profile.id,
                name=form.name.data.strip(),
                url=form.url.data.strip(),
                description=form.description.data or None
            )
            db.session.add(reg)
            db.session.commit()
            flash(f'"{reg.name}" has been linked to your profile!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('external_registry_form.html', form=form, profile=profile)

    @app.route('/external-registry/<int:reg_id>/delete', methods=['POST'])
    @login_required
    def delete_external_registry(reg_id):
        reg = ExternalRegistry.query.get_or_404(reg_id)
        if reg.profile.user_id != current_user.id:
            abort(403)
        name = reg.name
        db.session.delete(reg)
        db.session.commit()
        flash(f'"{name}" has been removed.', 'info')
        return redirect(url_for('dashboard'))

    @app.route('/account', methods=['GET', 'POST'])
    @login_required
    def account_settings():
        form = AccountSettingsForm(obj=current_user)

        if form.validate_on_submit():
            # Check if email is changing
            new_email = form.email.data.lower().strip()
            if new_email != current_user.email:
                existing = User.query.filter_by(email=new_email).first()
                if existing:
                    flash('That email address is already in use.', 'danger')
                    return render_template('account_settings.html', form=form)
                current_user.email = new_email

            # Handle password change
            if form.new_password.data:
                if not form.current_password.data:
                    flash('Please enter your current password to set a new one.', 'danger')
                    return render_template('account_settings.html', form=form)
                if not current_user.check_password(form.current_password.data):
                    flash('Current password is incorrect.', 'danger')
                    return render_template('account_settings.html', form=form)
                current_user.set_password(form.new_password.data)

            db.session.commit()
            flash('Account settings updated successfully.', 'success')
            return redirect(url_for('account_settings'))

        return render_template('account_settings.html', form=form)

    @app.route('/account/delete', methods=['POST'])
    @login_required
    def delete_account():
        user = current_user
        logout_user()
        db.session.delete(user)
        db.session.commit()
        flash('Your account has been permanently deleted.', 'info')
        return redirect(url_for('index'))

    # ─────────────────────────────────────────────
    # Error handlers
    # ─────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created.")
    app.run(debug=True)
