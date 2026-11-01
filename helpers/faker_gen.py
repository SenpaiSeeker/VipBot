from faker import Faker

from .patcher import DataObject, Object


class FakeInfoGenerator(Object):
    _ns_alias = "faker"

    def __init__(self, client=None, locale: str = "id_ID"):
        super().__init__(client)
        self.fake = Faker(locale)

    def generate(self) -> DataObject:
        profile = self.fake.profile()
        return DataObject(
            name=profile.get("name"),
            address=profile.get("address"),
            email=profile.get("mail"),
            job=profile.get("job"),
            company=profile.get("company"),
            phone_number=self.fake.phone_number(),
            birthdate=profile.get("birthdate"),
            website=self.fake.url(),
        )
