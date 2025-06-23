exports.rossum_hook_request_handler = async ({
  configure,
  secrets,
  payload,
  settings,
  variant,
  form,
  hook_interface,
}) => {
  const findData = async (dataset) => {
    const response = await fetch(`${url}/v1/data/find`, {
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
        dataset,
      }),
    });

    return await response.json();
  };

  const findDatasets = async () => {
    const response = await fetch(`${url}/v2/dataset/`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${secrets.token}`,
      },
    });

    return await response.json();
  }

  const url =
    settings.url || "https://elis.master.r8.lol/svc/master-data-hub/api";

  if (variant === "show_master_data") {
    if (form && form.dataset) {
      const data = await findData(form.dataset);

      return {
        intent: {
          form: {
            width: 600,
            defaultValue: {
              results: data.results.map(result => ({ ...result, id: result._id })),
            },
            uiSchema: {
              type: "Group",
              elements: [{
                type: "Table",
                scope: "#/properties/results",
              }, ],
            },
          },
        },
      };
    }

    const datasets = await findDatasets()

    return {
      intent: {
        form: {
          hook_interface,
          schema: {
            type: "object",
            properties: {
              dataset: {
                type: "string",
                enum: datasets.datasets.map((d) => d.dataset_name),
              },
            },
          },
        },
      },
    };
  }

  if (configure === true) {
    const datasets = await findDatasets()

    return {
      intent: {
        form: {
          schema: {
            type: "object",
            properties: {
              dataset: {
                type: "string",
                enum: datasets.datasets.map((d) => d.dataset_name),
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
    const data = await findData(payload.dataset);

    return {
      options: data.results.map((result) => ({
        value: result[payload.value_key],
        label: result[payload.label_key],
      })),
      value: data.results[0][payload.value_key],
    };
  }
};