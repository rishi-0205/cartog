/** KafkaJS producer and consumer — send/eachMessage. */
import { Kafka } from "kafkajs";
const producer = new Kafka({ brokers: [] }).producer();
export async function sendKafka(topic: string, data: unknown): Promise<void> { await producer.send({ topic, messages: [{ value: JSON.stringify(data) }] }); }
export async function handleMessage(m: unknown): Promise<void> { console.log(m); }
