"""Post-import sanity check for the Flipkart 2018 load."""
import sqlite3

con = sqlite3.connect("bazaarpulse.db")
cur = con.cursor()

print("products:     ", cur.execute("SELECT COUNT(*) FROM products").fetchone()[0])
print("categories:   ", cur.execute("SELECT COUNT(DISTINCT category) FROM products").fetchone()[0])
print("brands:       ", cur.execute("SELECT COUNT(DISTINCT brand) FROM products").fetchone()[0])
print("with image:   ", cur.execute("SELECT COUNT(*) FROM products WHERE image_url LIKE 'http%'").fetchone()[0])
print("price history:", cur.execute("SELECT COUNT(*) FROM price_history").fetchone()[0])
print("rated rows:   ", cur.execute("SELECT COUNT(*) FROM products WHERE rating > 0").fetchone()[0])
print()
print("category distribution:")
for cat, n in cur.execute(
    "SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC LIMIT 15"
):
    print(f"  {cat:22} {n:>6}")
print()
print("sample rows:")
for row in cur.execute(
    "SELECT id, substr(name,1,38), brand, category, current_price, mrp, discount_pct, rating "
    "FROM products LIMIT 5"
):
    print(" ", row)
