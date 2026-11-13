from uuid import UUID, uuid4


class Ids:
    @staticmethod
    def new_id() -> UUID:
        return uuid4()
