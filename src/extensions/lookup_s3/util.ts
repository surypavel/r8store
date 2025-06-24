import {
  S3Client,
  GetObjectCommand,
  PutObjectCommand,
  ListBucketsCommand,
} from "@aws-sdk/client-s3";
import { Readable } from "stream";

// Initialize S3 client
export const createS3 = (
  settings: { endpoint: string, region: string },
  secrets: { accessKeyId: string; secretAccessKey: string }
) =>
  new S3Client({
    region: settings.region,
    endpoint: settings.endpoint,
    credentials: {
      accessKeyId: secrets.accessKeyId,
      secretAccessKey: secrets.secretAccessKey,
    },
  }); // Replace with your AWS region

// Convert Readable stream to string
const streamToString = (stream: Readable): Promise<string> =>
  new Promise((resolve, reject) => {
    const chunks: any[] = [];
    stream.on("data", (chunk) => chunks.push(chunk));
    stream.on("error", reject);
    stream.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
  });

/**
 * Read JSON file from S3 bucket
 */
export async function readJsonFromS3(
  s3: S3Client,
  bucketName: string,
  key: string
): Promise<any> {
  try {
    const command = new GetObjectCommand({ Bucket: bucketName, Key: key });
    const response = await s3.send(command);
    const body = await streamToString(response.Body as Readable);
    return JSON.parse(body);
  } catch (error) {
    console.error("Error reading JSON from S3:", error);
    throw error;
  }
}

/**
 * Write JSON object to S3 bucket
 */
export async function writeJsonToS3(
  s3: S3Client,
  bucketName: string,
  key: string,
  data: any
): Promise<void> {
  try {
    const jsonString = JSON.stringify(data, null, 2); // Pretty print optional
    const command = new PutObjectCommand({
      Bucket: bucketName,
      Key: key,
      Body: jsonString,
      ContentType: "application/json",
    });

    await s3.send(command);
    console.log(`Successfully wrote JSON to s3://${bucketName}/${key}`);
  } catch (error) {
    console.error("Error writing JSON to S3:", error);
    throw error;
  }
}

export async function listS3Buckets(s3: S3Client) {
  try {
    const command = new ListBucketsCommand({});
    const response = await s3.send(command);
    return response.Buckets;
  } catch (error) {
    console.error("Error listing buckets:", error);
  }
}
