import { WebClient } from '@slack/web-api';

const options = {};
const web = (token) => new WebClient(token, options);

export const sendSlackMessage = async (token, message, channel) => {
    return new Promise(async (resolve, reject) => {
        const channelId = channel;
        try {
            const resp = await web(token).chat.postMessage({
                blocks: message,
                channel: channelId,
            });
            return resolve(true);
        } catch (error) {
            return resolve(true);
        }
    });
};