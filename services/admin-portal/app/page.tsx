export default async function Page() {
  // Prosty panel pingujący API
  const res = await fetch(process.env.NEXT_PUBLIC_API_URL + "/healthz", { cache: "no-store" });
  const health = await res.json();
  return (
    <main style={{padding: 24}}>
      <h1>AstraDesk — Admin Portal</h1>
      <p>API health: {health.status}</p>
      <p>Wyślij zapytanie do agenta (curl):</p>
      <pre>
        {`curl -s $API/v1/agents/run -H 'content-type: application/json' -d '{"agent":"support","input":"Utwórz ticket na ..."}'`}
      </pre>
    </main>
  );
}
