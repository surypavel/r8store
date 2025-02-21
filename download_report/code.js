exports.rossum_hook_request_handler = async ({
  rossum_authorization_token,
  base_url,
}) => {
  const response = await fetch(`${base_url}/api/v1/annotations/search`, {
    method: "POST",
    headers: {
      "Authorization": `Token ${rossum_authorization_token}`
    }
  })

  const data = await response.json();

  return {
    intent: {
      info: {
        message: `Export is being downloaded.`,
      },
      download: {
        filename: "export.csv",
        content: data.results.map(result => `${result.id},${result.created_at}`).join("\n")
      }
    }
  }
};

