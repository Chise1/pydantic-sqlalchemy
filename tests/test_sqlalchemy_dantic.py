from datetime import datetime, timezone
from typing import List

import pytest
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, joinedload, relationship, sessionmaker
from sqlalchemy_dantic import sqlalchemy_to_pydantic
from sqlalchemy_utc import UtcDateTime

Base = declarative_base()

engine = create_engine("sqlite://", echo=True)


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), comment="name")
    fullname = Column(String)
    nickname = Column(String)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(UtcDateTime, default=utc_now, onupdate=utc_now)

    addresses = relationship(
        "Address", back_populates="user", cascade="all, delete, delete-orphan"
    )


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


Base.metadata.create_all(engine)

LocalSession = sessionmaker(bind=engine)

db: Session = LocalSession()

ed_user = User(name="ed", fullname="Ed Jones", nickname="edsnickname")

address = Address(email_address="ed@example.com")
address2 = Address(email_address="eddy@example.com")
ed_user.addresses = [address, address2]
db.add(ed_user)
user_no_address = User(name="noo", fullname="NoneAddress", nickname="NoneAddress")
db.add(user_no_address)
db.commit()


def test_defaults() -> None:
    PydanticUser = sqlalchemy_to_pydantic(User, name="PydanticUser")
    PydanticAddress = sqlalchemy_to_pydantic(Address, name="PydanticAddress")

    class PydanticUserWithAddresses(PydanticUser):
        addresses: List[PydanticAddress] = []

    user = db.query(User).first()
    pydantic_user = PydanticUser.from_orm(user)
    data = pydantic_user.dict()
    assert isinstance(data["created"], datetime)
    assert isinstance(data["updated"], datetime)
    check_data = data.copy()
    del check_data["created"]
    del check_data["updated"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "nickname": "edsnickname",
    }
    pydantic_user_with_addresses = PydanticUserWithAddresses.from_orm(user)
    data = pydantic_user_with_addresses.dict()
    assert isinstance(data["updated"], datetime)
    assert isinstance(data["created"], datetime)
    check_data = data.copy()
    del check_data["updated"]
    del check_data["created"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "nickname": "edsnickname",
        "addresses": [
            {"email_address": "ed@example.com", "id": 1, "user_id": 1},
            {"email_address": "eddy@example.com", "id": 2, "user_id": 1},
        ],
    }


def test_schema() -> None:
    PydanticUser = sqlalchemy_to_pydantic(User, name="PydanticUserSchema")
    PydanticAddress = sqlalchemy_to_pydantic(Address, name="PydanticAddressSchema")
    print(PydanticUser.schema())
    assert PydanticUser.schema() == {
        "title": "PydanticUserSchema",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "name": {
                "title": "Name",
                "description": "name",
                "maxLength": 32,
                "type": "string",
            },
            "fullname": {"title": "Fullname", "type": "string"},
            "nickname": {"title": "Nickname", "type": "string"},
            "created": {"title": "Created", "type": "string", "format": "date-time"},
            "updated": {"title": "Updated", "type": "string", "format": "date-time"},
        },
        "required": ["id"],
    }
    assert PydanticAddress.schema() == {
        "title": "PydanticAddressSchema",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "email_address": {"title": "Email Address", "type": "string"},
            "user_id": {"title": "User Id", "type": "integer"},
        },
        "required": ["id", "email_address"],
    }


def test_config() -> None:
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

        @classmethod
        def alias_generator(cls, string: str) -> str:
            pascal_case = "".join(word.capitalize() for word in string.split("_"))
            camel_case = pascal_case[0].lower() + pascal_case[1:]
            return camel_case

    PydanticUser = sqlalchemy_to_pydantic(User, name="PydanticUserConfig")
    PydanticAddress = sqlalchemy_to_pydantic(
        Address, name="PydanticAddressConfig", config=Config
    )

    class PydanticUserWithAddresses(PydanticUser):
        addresses: List[PydanticAddress] = []

    user = db.query(User).first()
    pydantic_user_with_addresses = PydanticUserWithAddresses.from_orm(user)
    data = pydantic_user_with_addresses.dict(by_alias=True)
    assert isinstance(data["created"], datetime)
    assert isinstance(data["updated"], datetime)
    check_data = data.copy()
    del check_data["created"]
    del check_data["updated"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "nickname": "edsnickname",
        "addresses": [
            {"emailAddress": "ed@example.com", "id": 1, "userId": 1},
            {"emailAddress": "eddy@example.com", "id": 2, "userId": 1},
        ],
    }


def test_exclude() -> None:
    PydanticUser = sqlalchemy_to_pydantic(
        User, name="PydanticUserExclude", exclude={"nickname"}
    )
    PydanticAddress = sqlalchemy_to_pydantic(
        Address, name="PydanticAddressExclude", exclude={"user_id"}
    )

    class PydanticUserWithAddresses(PydanticUser):
        addresses: List[PydanticAddress] = []

    user = db.query(User).first()
    pydantic_user_with_addresses = PydanticUserWithAddresses.from_orm(user)
    data = pydantic_user_with_addresses.dict(by_alias=True)
    assert isinstance(data["created"], datetime)
    assert isinstance(data["updated"], datetime)
    check_data = data.copy()
    del check_data["created"]
    del check_data["updated"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "addresses": [
            {"email_address": "ed@example.com", "id": 1},
            {"email_address": "eddy@example.com", "id": 2},
        ],
    }


def test_relations() -> None:
    PydanticUser = sqlalchemy_to_pydantic(
        User,
        name="PydanticUserRelation",
        include=(
            "id",
            "name",
            "addresses",
            "addresses.email_address",
            "addresses.id",
            "addresses.user_id",
        ),
        depth=1,
    )
    PydanticAddress = sqlalchemy_to_pydantic(
        Address,
        name="PydanticAddressRelation",
        exclude=("user.created", "user.updated"),
        depth=2,
    )
    user = db.query(User).options(joinedload(User.addresses)).first()
    addresses = db.query(Address).options(joinedload(Address.user))
    pydantic_user = PydanticUser.from_orm(user)
    pydantic_addresses = [PydanticAddress.from_orm(address) for address in addresses]
    address_data = [i.dict() for i in pydantic_addresses]
    data = pydantic_user.dict()
    check_data = data.copy()
    assert check_data == {
        "id": 1,
        "name": "ed",
        "addresses": [
            {"email_address": "ed@example.com", "id": 1, "user_id": 1},
            {"email_address": "eddy@example.com", "id": 2, "user_id": 1},
        ],
    }
    assert address_data.copy() == [
        {
            "email_address": "ed@example.com",
            "id": 1,
            "user_id": 1,
            "user": {
                "id": 1,
                "name": "ed",
                "fullname": "Ed Jones",
                "nickname": "edsnickname",
            },
        },
        {
            "email_address": "eddy@example.com",
            "id": 2,
            "user_id": 1,
            "user": {
                "id": 1,
                "name": "ed",
                "fullname": "Ed Jones",
                "nickname": "edsnickname",
            },
        },
    ]
    user2 = (
        db.query(User)
        .filter(User.name == "noo")
        .options(joinedload(User.addresses))
        .first()
    )
    pydantic_user2 = PydanticUser.from_orm(user2)
    data2 = pydantic_user2.dict()
    check_data2 = data2.copy()
    assert check_data2 == {
        "id": 2,
        "name": "noo",
        "addresses": [],
    }


def test_raiseinfo() -> None:
    with pytest.raises(AttributeError):
        sqlalchemy_to_pydantic(
            User, name="PydanticUserExclude",
        )
    with pytest.raises(AttributeError):
        sqlalchemy_to_pydantic(
            User, name="PydanticUserRaise", include=["name"], exclude=["nickname"]
        )
