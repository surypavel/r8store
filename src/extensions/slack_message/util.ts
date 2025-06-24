import { WebClient } from '@slack/web-api';

const options = {};
const web = (token: string) => new WebClient(token, options);

export const sendSlackMessage = async (token: string, message: string, channel: string) => {
    return new Promise(async (resolve, reject) => {
        const channelId = channel;
        try {
            const resp = await web(token).chat.postMessage({
                text: message,
                channel: channelId,
            });
            return resolve(true);
        } catch (error) {
            return reject(error);
        }
    });
};