TORTOISE_ORM = {
    "connections": {
        "default": "postgres://user:password@localhost:5432/mydb"
    },
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default",
        }
    }
}