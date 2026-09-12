type Any = any;

function makeErr(name: string) {
    return class extends Error {
        constructor(message = "") {
            super(message);
            this.name = name;
        }
        static code = 400;
    };
}

export const MessageNotModified = makeErr("MessageNotModified");
export const MessageDeleteForbidden = makeErr("MessageDeleteForbidden");
export const UserIsBlocked = makeErr("UserIsBlocked");
export const UserNotParticipant = makeErr("UserNotParticipant");
export const ChatAdminRequired = makeErr("ChatAdminRequired");
export const PeerIdInvalid = makeErr("PeerIdInvalid");
export const BadRequest = makeErr("BadRequest");
export const FloodWait = makeErr("FloodWait");
export const ChatWriteForbidden = makeErr("ChatWriteForbidden");
export const MessageIdsEmpty = makeErr("MessageIdsEmpty");
export const ButtonDataInvalid = makeErr("ButtonDataInvalid");
export const MediaEmpty = makeErr("MediaEmpty");
export const MessageEmpty = makeErr("MessageEmpty");
export const UsernameNotOccupied = makeErr("UsernameNotOccupied");
export const UsernameInvalid = makeErr("UsernameInvalid");
export const UserAlreadyParticipant = makeErr("UserAlreadyParticipant");
export const ApiIdInvalid = makeErr("ApiIdInvalid");
export const ApiHashInvalid = makeErr("ApiHashInvalid");
export const BotMethodInvalid = makeErr("BotMethodInvalid");
export const QueryIdInvalid = makeErr("QueryIdInvalid");

export interface RPCErrorLike {
    className?: string;
    code?: number;
}

export function isErrorOf(e: unknown, Cls: Any): boolean {
    return e instanceof Cls;
}

export function messageExceptionName(e: Any): string {
    if (!e) {
        return "Unknown";
    }
    if (e.name && e.name !== "Error") {
        return e.name;
    }
    if (e.className) {
        return e.className;
    }
    return e.constructor?.name || "Error";
}

export const IGNORED_HANDLER_ERRORS: Any[] = [
    MessageNotModified,
    MessageDeleteForbidden,
];