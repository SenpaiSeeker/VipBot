import { faker } from "@faker-js/faker/locale/id_ID";

export interface FakeProfile {
    name: string;
    address: string;
    email: string;
    job: string;
    company: string;
    phone_number: string;
    birthdate: string;
    website: string;
}

export class FakeInfoGenerator {
    generate(): FakeProfile {
        return {
            name: faker.person.fullName(),
            address: faker.location.streetAddress(),
            email: faker.internet.email(),
            job: faker.person.jobTitle(),
            company: faker.company.name(),
            phone_number: faker.phone.number(),
            birthdate: faker.date
                .birthdate()
                .toISOString()
                .slice(0, 10),
            website: faker.internet.url(),
        };
    }
}