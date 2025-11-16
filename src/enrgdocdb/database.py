from flask_security.models import sqla as sqla
from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Model(DeclarativeBase):
    pass


db = SQLAlchemy()
sqla.FsModels.set_db_info(base_model=Model)
