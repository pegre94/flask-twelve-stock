import os
from itertools import groupby

import pandas as pd
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

# Init app
app = Flask(__name__)
CORS(app)
basedir = os.path.abspath(os.path.dirname(__file__))
# Database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "stock.sqlite"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
# Init db
db = SQLAlchemy(app)
# Init ma
ma = Marshmallow(app)
# CONSTANTS
CURRENCIES_EXCHANGE_SYMBOLS = {"NOK": "NOK/USD", "EUR": "EUR/USD"}
CAR_PRODUCERS = {
    "TYO": "Toyota Motor Corporation",
    "GM": "General Motors Company",
    "HMC": "Honda Motor Company",
    "RACE": "Ferrari N.V.",
    "F": "Ford Motor Company",
    "OSK": "Oshkosh Corporation",
    "TTM": "Tata Motors Limited",
}


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
def get_stocks():
    symbol = request.args.get("symbol")
    currency = request.args.get("currency", default="USD")
    output = request.args.get("output")

    def _apply_exchange_rate(stocks, currency):
        if currency == "USD":
            return stocks
        exchange = Currencies.query.filter(
            Currencies.symbol == CURRENCIES_EXCHANGE_SYMBOLS[currency]
        )
        i = 0
        for stock in stocks:
            try:
                curr_exchange = exchange[i]
            except IndexError:
                break
            # there are less exchange rates rows than stocks
            if stock.datetime != curr_exchange.datetime:
                while stock.datetime < curr_exchange.datetime:
                    try:
                        curr_exchange = exchange[i]
                    except IndexError:
                        break
                    i += 1

            stock.open = stock.open / curr_exchange.open
            stock.high = stock.high / curr_exchange.high
            stock.low = stock.low / curr_exchange.low
            stock.close = stock.close / curr_exchange.close
        return stocks

    if symbol:
        stocks = Stocks.query.filter(Stocks.symbol == symbol)
    else:
        stocks = Stocks.query.all()
    stocks = _apply_exchange_rate(stocks, currency)
    stocks_json = stocks_schema.dump(stocks)
    results = {}
    if output == "raw":
        return jsonify(stocks_json)
    # structurize results
    for key, group in groupby(stocks_json, key=lambda x: x["symbol"]):
        results[key] = {"full_name": CAR_PRODUCERS[key], "values": list(group)}

    return jsonify(results)


@app.route("/cagr", methods=["GET"])
def calculate_cagr():
    symbol = request.args.get("symbol")
    num_of_years = request.args.get("num_of_years")

    def _find_closest_to_date(basic_query, model, ts):
        import math

        # first check if row with ts exists
        if same_date := basic_query.filter(model.datetime == ts).first():
            return same_date
        # find the closest events which are greater/less than the timestamp
        gt_event = (
            basic_query.filter(model.datetime > ts)
            .order_by(model.datetime.asc())
            .first()
        )
        lt_event = (
            basic_query.filter(model.datetime < ts)
            .order_by(model.datetime.desc())
            .first()
        )

        # find diff between events and the ts, if no event found default to infintiy
        gt_diff = (gt_event.datetime - ts).total_seconds() if gt_event else math.inf
        lt_diff = (ts - lt_event.datetime).total_seconds() if lt_event else math.inf

        # return the newest event if it is closer to ts else older event
        # if an event is None its diff will always be greater as we set it to infinity
        return gt_event if gt_diff < lt_diff else lt_event

    end_date = datetime.now()

    def _get_cagr(stock, num_of_years):
        if num_of_years == "all":
            num_of_years = relativedelta(stocks[0].datetime, stocks[-1].datetime).years
        else:
            num_of_years = int(num_of_years)

        last_stock = _find_closest_to_date(stocks, Stocks, end_date)
        start_time = last_stock.datetime - relativedelta(years=num_of_years)
        first_stock = _find_closest_to_date(stocks, Stocks, start_time)
        cagr = (last_stock.close / first_stock.open) ** (1 / float(num_of_years)) - 1
        cagr_perc = round(cagr * 100, 2)
        return {
            "start_date": first_stock.datetime,
            "end_date": last_stock.datetime,
            "first_value": first_stock.open,
            "last_value": last_stock.close,
            "num_of_years": num_of_years,
            "CAGR": cagr_perc,
        }

    if symbol:
        stocks = Stocks.query.filter(Stocks.symbol == symbol)
        results = _get_cagr(stocks, num_of_years)
    else:

        # stocks = Stocks.query.all()
        # sorted_stocks = {}
        # for key, group in groupby(stocks, key=lambda x: x.symbol):
        #     cagr = _get_cagr(list(group), num_of_years)
        #     sorted_stocks[key] = cagr
        #     return sorted_stocks
        results = {}
        for symbol in CAR_PRODUCERS.keys():
            stocks = Stocks.query.filter(Stocks.symbol == symbol)
            results[symbol] = _get_cagr(stocks, num_of_years)
    return jsonify(results)


@app.route("/tests/")
def pandas_test():
    stock_stmt = select(Stocks).where(Stocks.symbol == "F")
    stock = pd.read_sql(stock_stmt, db.engine)
    exchange_stmt = select(Currencies).where(Currencies.symbol == "EUR/USD")
    exchange = pd.read_sql(exchange_stmt, db.engine)
    #     symbol = db.Column(db.String(255))
    # datetime = db.Column(db.DateTime)
    # open = db.Column(db.Float)
    # high = db.Column(db.Float)
    # low = db.Column(db.Float)
    # close = db.Column(db.Float)
    # volume = db.Column(db.Float)
    # pd.DataFrame(
    #     stock.values * exchange.values, columns=stock.columns, index=stock.index
    # )
    exchange = currencies_schema.dump(exchange.to_json)
    return jsonify(exchange)


# Init schema
stocks_schema = StocksSchema(many=True)
currencies_schema = CurrenciesSchema(many=True)


# Run server
if __name__ == "__main__":
    app.run()
