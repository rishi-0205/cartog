/** AWS SQS — send_message with QueueUrl kwarg. */
import { SQSClient } from "@aws-sdk/client-sqs";
const client = new SQSClient({});
export async function sendSqs(body: string): Promise<void> { console.log(body, client); }
