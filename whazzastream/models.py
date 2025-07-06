from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.mutable import MutableList, MutableDict
from datetime import date, datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),  unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    color    = db.Column(db.String(7),  default="#000000")
    font     = db.Column(db.String(120), nullable=True)
    is_active= db.Column(db.Boolean, default=True)

    points            = db.Column(db.Integer, default=0)
    unlocked_smilies  = db.Column(MutableList.as_mutable(JSON),
                                  default=lambda: ["melting"])
    effect_inventory  = db.Column(MutableDict.as_mutable(JSON), default=dict)

    last_daily_bonus  = db.Column(db.Date,     nullable=True)
    last_stream_bonus = db.Column(db.DateTime, nullable=True)

class Message(db.Model):
    __tablename__ = "messages"

    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    text     = db.Column(db.Text,        nullable=False)
    color    = db.Column(db.String(7),   nullable=True)
    font     = db.Column(db.String(120), nullable=True)
    effect   = db.Column(db.String(40),  nullable=True)
    timestamp= db.Column(db.DateTime, server_default=db.func.now())

class StreamKey(db.Model):
    id  = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)

class Setting(db.Model):
    id                    = db.Column(db.Integer, primary_key=True)
    stream_suffix         = db.Column(db.String(255), default="whazzaStream")
    daily_bonus           = db.Column(db.Integer, default=20)
    stream_bonus_points   = db.Column(db.Integer, default=20)
    stream_bonus_interval = db.Column(db.Integer, default=30)
    smilie_cost           = db.Column(db.Integer, default=50)
    color_cost            = db.Column(db.Integer, default=200)
    font_cost             = db.Column(db.Integer, default=300)
    effect_cost           = db.Column(db.Integer, default=25)

    hls_secret            = db.Column(db.String(255), nullable=False,
                                      default="yxHj73XYGFSDbdhskd0561Hbljg")

