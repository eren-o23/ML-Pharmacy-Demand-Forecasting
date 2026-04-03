import { prisma } from '@/lib/db';
import ForecastChart from '@/components/ForecastChart';
import { notFound } from 'next/navigation';

async function getDrugDetails(drugId: number) {
  const drug = await prisma.drug.findUnique({
    where: { id: drugId },
  });

  if (!drug) return null;

  // Get all sales (or limit to last 365 days for performance)
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 10); // Get last 10 years to include 2019 data

  const sales = await prisma.salesDaily.findMany({
    where: {
      drugId,
      date: {
        gte: oneYearAgo,
      },
    },
    orderBy: {
      date: 'asc',
    },
  });

  // Get latest forecasts (deduplicated by date)
  const latestRun = await prisma.forecastDaily.findFirst({
    where: { drugId },
    orderBy: { runTimestamp: 'desc' },
    select: { runTimestamp: true },
  });

  let forecasts: any[] = [];
  
  if (latestRun) {
    
    // Get forecasts from the latest run (using gte to handle timestamp precision)
    const allForecasts = await prisma.forecastDaily.findMany({
      where: {
        drugId,
        runTimestamp: {
          gte: latestRun.runTimestamp,
        },
      },
      orderBy: {
        forecastDate: 'asc',
      },
    });
    
    // Deduplicate by date (keep first occurrence for each date)
    const seen = new Set();
    forecasts = allForecasts.filter(f => {
      const dateKey = f.forecastDate.toISOString();
      if (seen.has(dateKey)) return false;
      seen.add(dateKey);
      return true;
    });
  }

  return { drug, sales, forecasts, latestRun };
}

export default async function DrugDetailPage({
  params,
}: {
  params: { drugId: string };
}) {
  const drugId = parseInt(params.drugId);
  if (isNaN(drugId)) {
    notFound();
  }

  const data = await getDrugDetails(drugId);
  if (!data) {
    notFound();
  }

  const { drug, sales, forecasts, latestRun } = data;

  // Prepare chart data
  const salesChartData = sales.map(s => ({
    date: s.date.toISOString().split('T')[0],
    actual: s.quantitySold,
  }));

  const forecastChartData = forecasts.map(f => ({
    date: f.forecastDate.toISOString().split('T')[0],
    predicted: Number(f.predictedDemand),
    lowerCi: f.lowerCi ? Number(f.lowerCi) : undefined,
    upperCi: f.upperCi ? Number(f.upperCi) : undefined,
  }));

  const combinedChartData = [...salesChartData, ...forecastChartData];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <a href="/drugs" className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block">
          ← Back to Drugs
        </a>
        <h1 className="text-3xl font-bold text-gray-900">{drug.drugName}</h1>
        <p className="text-gray-600 mt-1">
          Code: {drug.drugCode} | ATC: {drug.atcCode || 'N/A'}
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 uppercase">Sales Records</h3>
          <p className="text-3xl font-bold text-blue-600 mt-2">{sales.length}</p>
          <p className="text-xs text-gray-500 mt-1">Historical data</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 uppercase">Forecast Points</h3>
          <p className="text-3xl font-bold text-green-600 mt-2">{forecasts.length}</p>
          {latestRun && (
            <p className="text-xs text-gray-500 mt-1">
              Last run: {new Date(latestRun.runTimestamp).toLocaleDateString()}
            </p>
          )}
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 uppercase">Avg Daily Demand</h3>
          <p className="text-3xl font-bold text-purple-600 mt-2">
            {sales.length > 0
              ? (sales.reduce((sum, s) => sum + s.quantitySold, 0) / sales.length).toFixed(1)
              : '0'}
          </p>
          <p className="text-xs text-gray-500 mt-1">Historical average</p>
        </div>
      </div>

      {/* Forecast Chart */}
      {combinedChartData.length > 0 ? (
        <ForecastChart
          data={combinedChartData}
          title="Historical Sales and Demand Forecast"
        />
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800 font-medium">No data available</p>
          <p className="text-yellow-700 text-sm mt-2">
            Run the ML pipeline to generate forecasts for this drug
          </p>
        </div>
      )}

      {/* Recent Sales Table */}
      {sales.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Sales (Last 10 days)</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Quantity Sold
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sales.slice(-10).reverse().map((sale) => (
                  <tr key={sale.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {sale.date.toISOString().split('T')[0]}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {sale.quantitySold}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
