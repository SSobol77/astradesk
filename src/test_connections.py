# services/api-gateway/src/test_connections.py
import asyncio
import asyncpg
import redis.asyncio as redis
import os

async def test_postgres():
    try:
        DATABASE_URL=postgresql://neondb_owner:npg_4gNCM6hoBUzO@ep-wild-union-aga560tn-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require
        print(f"🔄 Connecting to PostgreSQL: {DATABASE_URL.split('@')[1].split('/')[0]}")
        conn = await asyncpg.connect(DATABASE_URL)
        version = await conn.fetchval("SELECT version()")
        print(f"✅ PostgreSQL: Connected successfully!")
        print(f"   Database: {await conn.fetchval('SELECT current_database()')}")
        print(f"   User: {await conn.fetchval('SELECT current_user')}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False

async def test_redis():
    try:
        REDIS_URL=redis://default:gHAWqYKBgDKbkVOlvfFws8kKZ4gaNtTe@redis-10303.crce219.us-east-1-4.ec2.redns.redis-cloud.com:10303
        print(f"🔄 Connecting to Redis: {REDIS_URL.split('@')[1]}")
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        info = await r.info()
        print(f"✅ Redis: Connection successful!")
        print(f"   Version: {info.get('redis_version')}")
        print(f"   Memory: {info.get('used_memory_human')}")
        await r.close()
        return True
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False


async def main():
    print("🧪 Testing database connections...")
    print("=" * 50)
    
    pg_ok = await test_postgres()
    print("-" * 30)
    redis_ok = await test_redis()
    print("=" * 50)
    
    if pg_ok and redis_ok:
        print("🎉 All connections work! Application should start normally.")
    else:
        print("💥 Some connections failed. Check your configuration.")
        if not pg_ok:
            print("   - Verify Neon.tech database is running and credentials are correct")
        if not redis_ok:
            print("   - Verify Redis Cloud instance is active and credentials are correct")

if __name__ == "__main__":
    asyncio.run(main())