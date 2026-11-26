/** S3 upload utility — file storage spine. */
export async function uploadObject(key: string, body: string): Promise<void> {
  console.log(`upload ${key} ${body.length}`);
}
