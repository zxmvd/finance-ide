from cs50 import SQL
import os

total_share_value = db.execute("SELECT SUM(total) FROM portfolio")