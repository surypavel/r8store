exports.rossum_hook_request_handler = async ({
  hook,
  location,
  base_url,
  rossum_authorization_token
}) => {
  const docRegex = /document\/(\d+)/
  const docId = location.pathname.match(docRegex)?.[1]
  const docRequest = await fetch(`${base_url}/api/v1/annotations/${docId}/content`, {
    headers: {
      "Authorization": `Token ${rossum_authorization_token}`
    }
  })

  if (docRequest.status !== 200) {
    return {
      intent: {
        error: {
          message: "You need to be on the validation screen."
        }
      }
    }
  }

  const docResponse = await docRequest.json()
  const vendorAddress = findBySchemaId(docResponse.content, "sender_address")[0]?.content.value;

  if (!vendorAddress) {
    return {
      intent: {
        error: {
          message: "This document does not have vendor address."
        }
      }
    }
  }

  const vendorRequest = await fetch(`https://nominatim.openstreetmap.org/search.php?q=${vendorAddress}&format=jsonv2`);
  const vendorResponse = await vendorRequest.json()
  const first = vendorResponse[0]

  if (!first) {
    return {
      intent: {
        error: {
          message: "Vendor could not be found."
        }
      }
    }
  }

  const lat = first.lat
  const lng = first.lon

  const rainRequest = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m`)
  const rainResponse = await rainRequest.json()
  const currentTemperature = rainResponse.current.temperature_2m

  return {
    intent: {
      form: {
        schema: {},
        uiSchema: {
          type: 'VerticalLayout',
          elements: [{
              type: 'Typography',
              text: vendorAddress,
              variant: "caption",
              color: "text.disabled"
            },
            {
              type: 'Typography',
              text: `${currentTemperature <= 0 ? "❄️" : currentTemperature <= 20 ? `☁️` : '🌞'} ${currentTemperature} °C`,
              variant: "h2",
              fontWeight: "bold",
              color: currentTemperature <= 20 ? undefined : 'error',
            },
            {
              type: 'Typography',
              text: currentTemperature <= 0 ? "Not hot. Bring hot chocolate." : currentTemperature <= 20 ? `Not great, not terrible.` : 'Hot, bring ice cream.',
              fontWeight: "semibold",
              color: 'text.secondary',
              variant: "h5",
            },
          ],
        }
      }
    }

  };
};


const findBySchemaId = (content, schemaId) =>
  content.reduce(
    (results, dp) =>
    dp.schema_id === schemaId ? [...results, dp] :
    dp.children ? [...results, ...findBySchemaId(dp.children, schemaId)] :
    results,
    [],
  );
