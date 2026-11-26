/** TS decorator DI — Injectable/Inject. */
function Injectable(): ClassDecorator { return () => {}; }
function Inject(): ParameterDecorator { return () => {}; }
@Injectable()
export class Service { constructor(@Inject() dep: unknown) { void dep; } run(): void { return; } }
