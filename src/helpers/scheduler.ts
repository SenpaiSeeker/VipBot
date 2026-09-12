import cron from "node-cron";

type JobFunc = (...args: unknown[]) => unknown;

export class Scheduler {
    jobs: Array<[string, JobFunc]> = [];
    private _is_started = false;

    add_job(spec: string, func: JobFunc): void {
        this.jobs.push([spec, func]);
    }

    cron(spec: string): (func: JobFunc) => JobFunc {
        return <TArgs extends unknown[]>(
            func: (...args: TArgs) => unknown
        ): ((...args: TArgs) => unknown) => {
            const wrapped = (...args: TArgs) => func(...args);
            this.add_job(spec, wrapped as JobFunc);
            return wrapped;
        };
    }

    start(): void {
        if (this._is_started) {
            return;
        }
        for (const [spec, func] of this.jobs) {
            cron.schedule(spec, () => {
                void Promise.resolve(func()).catch((e) => {
                    console.error(`[Scheduler] job ${spec} error:`, e);
                });
            });
        }
        this._is_started = true;
    }
}