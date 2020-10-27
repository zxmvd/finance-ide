import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
# export API_KEY=pk_cb8187c1516c4a35a1a3b49a98fd045b
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
# if not os.environ.get("API_KEY"):
#     raise RuntimeError("API_KEY not set")




@app.route("/")
@login_required
def index():

    total_share_value = 0
    results = db.execute("SELECT shares, symbol FROM portfolio WHERE id=:id",
                        id = session["user_id"])


    for result in results:
        shares = result["shares"]
        symbol = result["symbol"]
        NewPrice = lookup(symbol)
        total = shares * NewPrice["price"]
        total_share_value +=  total
        db.execute("UPDATE portfolio SET price=:price, total=:total WHERE id =:id AND symbol=:symbol",
                    price=usd(NewPrice["price"]), total=usd(total), id=session["user_id"], symbol=symbol)

    holdings = db.execute("SELECT * FROM portfolio WHERE id = :id",
                          id=session["user_id"])

    cash_user = db.execute("SELECT cash FROM users WHERE id = :id",
                      id=session["user_id"])

    cash = cash_user[0]["cash"]
    total_value = total_share_value + cash


    return render_template("index.html", holdings=holdings, cash = usd(cash), total_value = usd(total_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        share = int(request.form.get("shares"))
        result = lookup(request.form.get("symbol"))
        #price = result['price']
        #userid = session['user_id']
        #return {result["price"]}
        if result != None:
            cash = db.execute("SELECT cash FROM users WHERE id = :userid",
                                userid=session['user_id'])

            if not cash or float(cash[0]["cash"]) < result["price"] * share:
                return apology("Not enough money")

            db.execute("INSERT INTO histories (symbol, shares, price, id) \
                    VALUES(:symbol, :shares, :price, :id)", \
                    symbol=result["symbol"], shares=share, \
                    price=usd(result["price"]), id=session["user_id"])

            db.execute("UPDATE users SET cash = cash - :purchase WHERE id = :id", \
                    id=session["user_id"], \
                     purchase=result["price"] * float(share))

            user_shares = db.execute("SELECT shares FROM portfolio \
                           WHERE id = :id AND symbol=:symbol", \
                           id=session["user_id"], symbol=result["symbol"])

            if not user_shares:
                db.execute("INSERT INTO portfolio (name, shares, price, total, symbol, id) \
                        VALUES(:name, :shares, :price, :total, :symbol, :id)", \
                        name=result["name"], shares=share, price=usd(result["price"]), \
                        total=usd(share * result["price"]), \
                        symbol=result["symbol"], id=session["user_id"])

            # Else increment the shares count
            else:
                shares_total = user_shares[0]["shares"] + share
                db.execute("UPDATE portfolio SET shares=:shares \
                        WHERE id=:id AND symbol=:symbol", \
                        shares=shares_total, id=session["user_id"], \
                        symbol=result["symbol"])

            flash("BOUGHT!")
            return redirect("/")

        else:
            return apology("Invalid Symbol")




    #         if pay > cash:
    #             return apology("No Sufficient Fund")
    #         else:
    #             newcash = cash - pay
    #             db.execute("UPDATE users SET cash = newcash WHERE id = userid")
    #             return render_template("quote.html")
    #     else:
    #         return apology("Invalid Symbol", 400)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT * FROM histories WHERE id=:id", id=session["user_id"])


    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]


        # Redirect user to home page

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("quote")
        result = lookup(symbol)
        if result != None:
            return render_template("quoted.html", result = result)
        else:
            return apology("Invalid Symbol", 400)

    else:
        return render_template("quote.html")


    #return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)


        elif not request.form.get("passwordRe"):
            return apology("must provide password", 403)

        password1 = request.form.get("password")
        password2 = request.form.get("passwordRe")
        if password1 != password2:
            return apology("must provide same passwords", 403)


        hashNum = generate_password_hash(password1)
        username = request.form.get("username")
        db.execute("INSERT INTO users ('username', 'hash') VALUES(?, ?)", username, hashNum)

        flash("registered!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


    #return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    holdings = db.execute("SELECT * FROM portfolio WHERE id=:id", id = session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    current_cash =  cash[0]["cash"]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares_for_sell = int(request.form.get("shares"))
        current_shares = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:symbol",\
                                     id=session["user_id"], symbol=symbol)
        updated_shares = current_shares[0]["shares"] - shares_for_sell
        stock_price = lookup(symbol)
        updated_price = stock_price["price"]
        cash_credit = shares_for_sell*updated_price
        updated_cash = current_cash + cash_credit

        if shares_for_sell > current_shares[0]["shares"]:
            return apology("YOU MUST SELL LESS SHARES")

        db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=updated_cash, id=session["user_id"])

        db.execute("INSERT INTO histories (symbol, shares, price, id) VALUES(:symbol, :shares, :price, :id)",\
                    symbol=symbol, shares=-shares_for_sell, price=usd(updated_price),\
                    id=session["user_id"])
        if updated_shares == 0:
            db.execute("DELETE FROM portfolio WHERE id=:id AND symbol=:symbol",
                       id=session["user_id"], symbol=symbol)
        else:
            db.execute("UPDATE portfolio SET shares=:shares, price=:price, total=:total \
                   WHERE id=:id AND symbol=:symbol",\
                   shares=updated_shares, price=usd(updated_price), total=usd(updated_shares*updated_price),\
                   id=session["user_id"], symbol=symbol)

        flash("SOLD!")
        return redirect("/")

    else:
        return render_template("sell.html", holdings=holdings)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
