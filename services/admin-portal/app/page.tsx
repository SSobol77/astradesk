// services/admin-portal/app/page.tsx
import { Suspense } from 'react';
import styles from './page.module.css'; // Dobra praktyka: style w osobnym module CSS

/**
 * Komponent HealthCheck asynchronicznie pobiera i wyświetla status API.
 * Jest opakowany w <Suspense>, aby w razie opóźnień lub błędów API
 * strona główna nadal się renderowała, pokazując fallback.
 */
async function HealthCheck() {
  let healthStatus: string;
  try {
    // Używamy `next: { revalidate: 10 }` zamiast `cache: "no-store"`,
    // aby uniknąć nadmiernego odpytywania API, ale jednocześnie
    // zapewnić odświeżanie danych co 10 sekund.
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/healthz`, {
      next: { revalidate: 10 },
    });

    if (!res.ok) {
      throw new Error(`API returned status: ${res.status}`);
    }
    const health = await res.json();
    healthStatus = health.status === 'ok' ? '✅ Online' : '⚠️ Offline';
  } catch (error) {
    console.error('Failed to fetch API health:', error);
    healthStatus = '❌ Error';
  }

  return <p>API Health Status: <strong>{healthStatus}</strong></p>;
}

/**
 * Strona główna panelu administracyjnego AstraDesk.
 * 
 * Wyświetla podstawowe informacje o stanie systemu i przykładowe
 * polecenia do interakcji z API.
 */
export default function Page() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
  const exampleCurl = `curl -X POST ${apiUrl}/v1/agents/run \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \\
  -d '{"agent": "support", "input": "Utwórz ticket dla awarii sieci..."}'`;

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1 className={styles.title}>AstraDesk Admin Portal</h1>
        
        <div className={styles.card}>
          <h2>System Status</h2>
          <Suspense fallback={<p>Loading API status...</p>}>
            <HealthCheck />
          </Suspense>
        </div>

        <div className={styles.card}>
          <h2>Example API Call</h2>
          <p>Użyj poniższego polecenia, aby wysłać zapytanie do agenta wsparcia:</p>
          <pre className={styles.codeBlock}>
            <code>{exampleCurl}</code>
          </pre>
          <p><small>Pamiętaj, aby zastąpić <strong>&lt;YOUR_JWT_TOKEN&gt;</strong> swoim aktualnym tokenem.</small></p>
        </div>
      </div>
    </main>
  );
}