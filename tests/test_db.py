import pytest_asyncio
import aiosqlite
import asyncio
import pytest
from src.services.db_service import ModDB
import datetime

@pytest_asyncio.fixture
async def moddb():
    db_file = "test.db"
    db = ModDB(db_file)
    await db.connect()
    yield db
    await db.close()

#=============APPEND USER TESTS================
@pytest.mark.asyncio
async def test_append_user_username_and_userid(moddb):
    await moddb.append_user(user_id=12,username="John")
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ? AND username = ?)", (12, "John"))
    result = await cursor.fetchone()
    user_exists =  bool(result[0]) if result else False

    assert user_exists is True

@pytest.mark.asyncio
async def test_append_user_username(moddb):
    with pytest.raises(TypeError):
        await moddb.append_user(username="Pete")
    
@pytest.mark.asyncio
async def test_append_user_userid(moddb):
    with pytest.raises(TypeError):
        await moddb.append_user(user_id=22)


#=============RECORD NOTES TESTS================
@pytest.mark.asyncio
async def test_record_note_user_exists(moddb):
    await moddb.append_user(user_id=12,username="John")

    await moddb.record_note(user_id=12, username="John", reason="Too cool")
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM notes WHERE user_id = ? AND content = ?)", (12, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

@pytest.mark.asyncio
async def test_record_note_user_doesnt_exist(moddb):
    await moddb.record_note(user_id=16, username="Philip", reason="Too cool")
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM notes WHERE user_id = ? AND content = ?)", (16, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

@pytest.mark.asyncio
async def test_record_note_user_doesnt_exist_only_username(moddb):
    with pytest.raises(TypeError):
        await moddb.record_note( username="Fan", reason="Too cool")

@pytest.mark.asyncio
async def test_record_note_user_doesnt_exist_only_userid(moddb):
    with pytest.raises(TypeError):
        await moddb.record_note( user_id=23, reason="Too cool")

@pytest.mark.asyncio
async def test_record_note_via_username(moddb):
    await moddb.append_user(user_id=12,username="John")

    await moddb.record_note(username="John", reason="Too cool")
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM notes WHERE user_id = ? AND content = ?)", (12, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

@pytest.mark.asyncio
async def test_record_note_via_userid(moddb):
    await moddb.append_user(user_id=12,username="John")

    await moddb.record_note(user_id=12, reason="Too cool")
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM notes WHERE user_id = ? AND content = ?)", (12, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True


#=============RECORD BAN TESTS================
@pytest.mark.asyncio
async def test_record_ban_user_exists(moddb):
    await moddb.append_user(user_id=12,username="John")

    await moddb.record_ban(user_id=12, username="John", reason="Too cool",unban_date=datetime.datetime.now())
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM bans WHERE user_id = ? AND content = ?)", (12, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

@pytest.mark.asyncio
async def test_record_ban_user_doesnt_exist(moddb):
    await moddb.record_ban(user_id=16, username="Philip", reason="Too cool", unban_date=datetime.datetime.now())
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM notes WHERE user_id = ? AND content = ?)", (16, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

@pytest.mark.asyncio
async def test_record_ban_user_doesnt_exist_only_username(moddb):
    with pytest.raises(TypeError):
        await moddb.record_ban( username="Fan", reason="Too cool", unban_date=datetime.datetime.now())

@pytest.mark.asyncio
async def test_record_ban_user_doesnt_exist_only_userid(moddb):
    with pytest.raises(TypeError):
        await moddb.record_ban( user_id=23, reason="Too cool", unban_date=datetime.datetime.now())

@pytest.mark.asyncio
async def test_record_ban_via_username(moddb):
    await moddb.append_user(user_id=12,username="John")

    await moddb.record_ban(username="John", reason="Too cool", unban_date=datetime.datetime.now())
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM bans WHERE user_id = ? AND content = ?)", (12, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

@pytest.mark.asyncio
async def test_record_ban_via_userid(moddb):
    await moddb.append_user(user_id=12,username="John")

    await moddb.record_ban(user_id=12, reason="Too cool", unban_date=datetime.datetime.now())
    cursor = await moddb.db.execute("SELECT EXISTS(SELECT 1 FROM bans WHERE user_id = ? AND content = ?)", (12, "Too cool"))
    result = await cursor.fetchone()
    exists =  bool(result[0]) if result else False

    assert exists is True

# TODO WRITE MORE TESTS