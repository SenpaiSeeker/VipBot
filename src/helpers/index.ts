import { TelegramClient } from "teleproto";
import { Argument } from "./argument";
import { Button } from "./button";
import { DashboardGenerator } from "./dashboardGen";
import { EmojiParse } from "./emojiParse";
import { FakeInfoGenerator } from "./fakerGen";
import { Gradient } from "./gradient";
import { LoggerHandler } from "./logger";
import { ServerMonitor } from "./monitor";
import { SaweriaScraper } from "./saweriaScraper";

export class CleanNamespace {
    telegram: { arg: Argument; button: Button };
    utils: {
        log: LoggerHandler;
        faker: FakeInfoGenerator;
        grad: Gradient;
        dashboard: DashboardGenerator;
    };
    server: { monitor: ServerMonitor };
    payment: { SaweriaScraper: typeof SaweriaScraper };
    emoji: EmojiParse;

    constructor(client: TelegramClient) {
        this.telegram = {
            arg: new Argument(client),
            button: new Button(),
        };
        this.utils = {
            log: new LoggerHandler(),
            faker: new FakeInfoGenerator(),
            grad: new Gradient(),
            dashboard: new DashboardGenerator(),
        };
        this.server = {
            monitor: new ServerMonitor(),
        };
        this.payment = {
            SaweriaScraper: SaweriaScraper,
        };
        this.emoji = new EmojiParse();
    }
}

const NS_SYMBOL = Symbol("vvip_clean_ns");

export function getNs(self: TelegramClient): CleanNamespace {
    const anySelf = self as unknown as Record<symbol, CleanNamespace>;
    if (!anySelf[NS_SYMBOL]) {
        anySelf[NS_SYMBOL] = new CleanNamespace(self);
    }
    return anySelf[NS_SYMBOL];
}

Object.defineProperty(TelegramClient.prototype, "ns", {
    get(this: TelegramClient) {
        return getNs(this);
    },
    configurable: true,
});