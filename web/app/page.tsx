import { prisma } from '@/lib/db';
import RiskBadge from '@/components/RiskBadge';

async function getDashboardData() {
  const drugs = await prisma.drug.findMany({
    include: {
      _count: {
        select: {
          forecastsDaily: true,
          salesDaily: true,
        },
      },
    },
  });

  // Get latest forecasts for risk analysis
  const latestForecasts = await prisma.$queryRaw<any[]>`
    SELECT 
      d.id,
      d.drug_code,
      d.drug_name,
      AVG(f.predicted_demand) as avg_forecast,
      MAX(f.run_timestamp) as latest_run
    FROM drugs d
    LEFT JOIN forecasts_daily f ON d.id = f.drug_id
    WHERE f.run_timestamp = (
      SELECT MAX(run_timestamp) FROM forecasts_daily WHERE drug_id = d.id
    )
    GROUP BY d.id, d.drug_code, d.drug_name
    ORDER BY avg_forecast DESC
    LIMIT 10
  `;

  return { drugs, latestForecasts };
}

export default async function Home() {
  const { drugs, latestForecasts } = await getDashboardData();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Pharmacy Demand Forecasting Dashboard
        </h1>
        <p className="text-gray-600">
          ML-powered demand forecasting for pharmaceutical inventory management
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 uppercase">Total Drugs</h3>
          <p className="text-3xl font-bold text-blue-600 mt-2">{drugs.length}</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 uppercase">Drugs with Forecasts</h3>
          <p className="text-3xl font-bold text-green-600 mt-2">
            {drugs.filter(d => (d._count?.forecastsDaily || 0) > 0).length}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 uppercase">Total Sales Records</h3>
          <p className="text-3xl font-bold text-purple-600 mt-2">
            {drugs.reduce((sum, d) => sum + (d._count?.salesDaily || 0), 0)}
          </p>
        </div>
      </div>

      {/* Top Forecasted Drugs */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Top Forecasted Drugs by Average Demand
        </h2>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                  Drug Code
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                  Drug Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                  Avg Forecast Demand
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                  Risk Level
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {latestForecasts.map((forecast) => {
                const avgDemand = Number(forecast.avg_forecast) || 0;
                const risk = avgDemand > 1000 ? 'high' : avgDemand > 500 ? 'medium' : 'low';
                
                return (
                  <tr key={forecast.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {forecast.drug_code}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {forecast.drug_name}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {avgDemand.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <RiskBadge risk={risk} />
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <a
                        href={`/drugs/${forecast.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Details →
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">Quick Actions</h3>
        <div className="flex gap-4">
          <a
            href="/drugs"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            View All Drugs
          </a>
          <button
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
            disabled
          >
            Run New Forecast (ML Pipeline)
          </button>
        </div>
      </div>
    </div>
  );
}
