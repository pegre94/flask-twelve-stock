#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os

# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
# Database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "stock.sqlite"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Init db
db = SQLAlchemy(app)
# Init ma
ma = Marshmallow(app)


class Stocks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(255))
    datetime = db.Column(db.DateTime)
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    close = db.Column(db.Float)
    volume = db.Column(db.Float)


class Currencies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(255))
    datetime = db.Column(db.DateTime)
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    close = db.Column(db.Float)


class StocksSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Stocks


class CurrenciesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Currencies


@app.route("/stocks/", methods=["GET"])
def get_products():
    all_products = Stocks.query.all()
    results = stocks_schema.dump(all_products)
    return jsonify(results)


# http://localhost:5000/stocks/F?currency=EUR
@app.route("/stocks/<symbol>", methods=["GET"])
def get_products_with_symbol(symbol):
    # currency = request.args.get("currency", default="USD")
    # exchange = Currencies.query.all()
    # exchange_results = currencies_schema.dump(exchange)
    products_with_symbol = Stocks.query.filter(Stocks.symbol == symbol)
    results = stocks_schema.dump(products_with_symbol)
    return jsonify(results)
    # return currency
    # return jsonify(exchange_results)


# Init schema
stocks_schema = StocksSchema(many=True)
currencies_schema = CurrenciesSchema(many=True)


# Run server
if __name__ == "__main__":
    app.run()
