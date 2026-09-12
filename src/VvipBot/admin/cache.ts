const TTL = 300;

export class UserCache {
    private _store: Record<number, [any, number]> = {};

    get(user_id: number): any {
        const entry = this._store[user_id];
        if (entry && Date.now() / 1000 - entry[1] < TTL) {
            return entry[0];
        }
        return undefined;
    }

    set(user_id: number, user_obj: any): void {
        this._store[user_id] = [user_obj, Date.now() / 1000];
    }

    invalidate(user_id: number): void {
        delete this._store[user_id];
    }

    clear(): void {
        this._store = {};
    }
}

export const _user_cache = new UserCache();