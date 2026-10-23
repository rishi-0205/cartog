import { formatGreeting } from '@core/utils';
import { CoreService } from '@monorepo/core';

export function runWebApp(): void {
  const service = new CoreService();
  console.log(formatGreeting('Cartog'), service.execute());
}
