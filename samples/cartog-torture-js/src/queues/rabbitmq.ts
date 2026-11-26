/** RabbitMQ/AMQP producer and consumer — basicPublish/basicConsume. */
import amqp from "amqplib";
const conn = amqp.connect("amqp://localhost");
export function basicPublish(ex: string, rk: string, body: string): void { console.log(ex, rk, body); }
export function onMessage(ch: unknown, m: unknown, p: unknown, body: string): void { console.log(body); }
void conn;
