exports.rossum_hook_request_handler = async ({ configure, secrets, payload, settings }) => {
  const url = settings.url || "https://elis.master.r8.lol/svc/master-data-hub/api"

  if (configure === true) {
    const response = await fetch(
      `${url}/v2/dataset/`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${secrets.token}`,
        },
      }
    );

    const datasets = await response.json();

    return {
      intent: {
        form: {
          schema: {
            type: "object",
            properties: {
              dataset: {
                type: "string",
                enum: datasets.map((d) => d.dataset_name),
              },
              value_key: {
                type: "string",
              },
              label_key: {
                type: "string",
              },
            },
          },
        },
      },
    };
  } else {
    const response = await fetch(
      `${url}/v1/data/find`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${secrets.token}`,
        },
        body: JSON.stringify({
          find: {},
          projection: {},
          skip: 0,
          limit: 100,
          sort: {},
          dataset: payload.dataset,
        }),
      }
    )

    // Get results from response json
    const data = await response.json();

    return {
      options: data.results,
      value: data.results[0]
    }
  }
};
