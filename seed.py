#!/usr/bin/env python3
"""
Seed script: populates GradList with demo data for development/preview.
Run AFTER run.py has created the database once, or run this standalone
(it calls init_db itself).
"""
from app import app, init_db, hash_password, mutate_db, query_db

DEMO_USERS = [
    {
        "email": "jordan@example.com",
        "username": "jordansmith",
        "full_name": "Jordan Smith",
        "password": "password123",
        "bio": "Computer Science grad, Tennessee native.",
        "avatar_color": "#6C5CE7",
    },
    {
        "email": "alex@example.com",
        "username": "alexjohnson",
        "full_name": "Alex Johnson",
        "password": "password123",
        "bio": "Pre-Med, future doctor!",
        "avatar_color": "#00B894",
    },
]

DEMO_REGISTRIES = [
    {
        "username": "jordansmith",
        "title": "Jordan's Graduation Registry",
        "graduate_name": "Jordan Smith",
        "school": "University of Tennessee",
        "degree": "B.S. Computer Science",
        "grad_date": "May 2025",
        "description": "So excited to graduate and start my career in tech! Any support is so appreciated.",
        "cover_color": "#6C5CE7",
    },
    {
        "username": "alexjohnson",
        "title": "Alex's Med School Celebration",
        "graduate_name": "Alex Johnson",
        "school": "Vanderbilt University",
        "degree": "B.S. Biology (Pre-Med)",
        "grad_date": "May 2025",
        "description": "Next stop: medical school! Celebrating four amazing years.",
        "cover_color": "#00B894",
    },
]

DEMO_ITEMS = [
    {
        "registry_slug": "jordan-smith-jordans-graduation-registry",
        "title": "Apple AirPods Pro (2nd Gen)",
        "description": "For commuting and working from home. Lightning or USB-C both fine.",
        "price": 249.00,
        "quantity_needed": 1,
        "product_url": "https://www.amazon.com/dp/B0BDHWDR12",
        "category": "Tech & Electronics",
        "is_priority": 1,
    },
    {
        "registry_slug": "jordan-smith-jordans-graduation-registry",
        "title": "Laptop Stand — Adjustable Aluminum",
        "description": "For my desk setup at my new job.",
        "price": 45.99,
        "quantity_needed": 1,
        "product_url": "https://www.amazon.com/dp/B07DW2M5KT",
        "category": "Tech & Electronics",
        "is_priority": 0,
    },
    {
        "registry_slug": "jordan-smith-jordans-graduation-registry",
        "title": "Moleskine Notebook Set",
        "description": "Classic ruled notebooks for journaling.",
        "price": 24.99,
        "quantity_needed": 2,
        "product_url": "https://www.amazon.com/s?k=moleskine+notebook",
        "category": "Books & Education",
        "is_priority": 0,
    },
    {
        "registry_slug": "jordan-smith-jordans-graduation-registry",
        "title": "Professional Blazer — Navy",
        "description": "For interviews and first days. Size M preferred.",
        "price": 89.00,
        "quantity_needed": 1,
        "product_url": "https://www.target.com/c/blazers/-/N-5xtm2",
        "category": "Clothing & Accessories",
        "is_priority": 1,
    },
    {
        "registry_slug": "alex-johnson-alexs-med-school-celebration",
        "title": "Stethoscope — Littmann Classic III",
        "description": "Starting med school in the fall — this is a must-have!",
        "price": 199.00,
        "quantity_needed": 1,
        "product_url": "https://www.amazon.com/dp/B01MSODQ12",
        "category": "Career & Professional",
        "is_priority": 1,
    },
    {
        "registry_slug": "alex-johnson-alexs-med-school-celebration",
        "title": "First Aid Kit — Premium Home Set",
        "description": "A good starter kit for the apartment.",
        "price": 39.99,
        "quantity_needed": 1,
        "product_url": "https://www.amazon.com/s?k=first+aid+kit",
        "category": "Fitness & Wellness",
        "is_priority": 0,
    },
]

def slugify_simple(text):
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def run_seed():
    with app.app_context():
        init_db()

        for u in DEMO_USERS:
            existing = query_db("SELECT id FROM users WHERE email=?", [u["email"]], one=True)
            if not existing:
                mutate_db(
                    "INSERT INTO users (email, username, password_hash, full_name, bio, avatar_color) VALUES (?,?,?,?,?,?)",
                    [u["email"], u["username"], hash_password(u["password"]), u["full_name"], u["bio"], u["avatar_color"]],
                )
                print(f"  ✓ Created user: {u['email']}")
            else:
                print(f"  · Skipped existing user: {u['email']}")

        for r in DEMO_REGISTRIES:
            user = query_db("SELECT id FROM users WHERE username=?", [r["username"]], one=True)
            if not user:
                print(f"  ! User not found: {r['username']}, skipping registry.")
                continue

            slug_base = f"{r['graduate_name']}-{r['title']}"
            slug = slugify_simple(slug_base)

            existing = query_db("SELECT id FROM registries WHERE slug=?", [slug], one=True)
            if not existing:
                mutate_db(
                    """INSERT INTO registries
                       (user_id, slug, title, graduate_name, school, degree, grad_date, description, is_public, cover_color)
                       VALUES (?,?,?,?,?,?,?,?,1,?)""",
                    [user["id"], slug, r["title"], r["graduate_name"], r["school"],
                     r["degree"], r["grad_date"], r["description"], r["cover_color"]],
                )
                print(f"  ✓ Created registry: {r['title']} (slug: {slug})")
            else:
                print(f"  · Skipped existing registry: {r['title']}")

        for item in DEMO_ITEMS:
            reg = query_db("SELECT id FROM registries WHERE slug=?", [item["registry_slug"]], one=True)
            if not reg:
                print(f"  ! Registry not found: {item['registry_slug']}, skipping item.")
                continue
            mutate_db(
                """INSERT INTO registry_items
                   (registry_id, title, description, price, quantity_needed, product_url, category, is_priority)
                   VALUES (?,?,?,?,?,?,?,?)""",
                [reg["id"], item["title"], item["description"], item["price"],
                 item["quantity_needed"], item["product_url"], item["category"], item["is_priority"]],
            )
            print(f"  ✓ Added item: {item['title']}")

        print("\n✅ Seed complete! Log in with:")
        print("   jordan@example.com / password123")
        print("   alex@example.com   / password123")

if __name__ == "__main__":
    print("🌱 Seeding GradList demo data...")
    run_seed()
