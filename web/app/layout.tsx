import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Pharmacy Demand Forecasting',
  description: 'ML-powered demand forecasting dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="bg-blue-600 text-white shadow-lg">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">
                <a href="/">Pharmacy Forecast</a>
              </h1>
              <div className="flex gap-6">
                <a href="/" className="hover:text-blue-200">Dashboard</a>
                <a href="/drugs" className="hover:text-blue-200">Drugs</a>
              </div>
            </div>
          </div>
        </nav>
        <main className="container mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
