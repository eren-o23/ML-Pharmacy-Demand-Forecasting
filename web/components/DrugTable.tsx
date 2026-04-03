'use client';

interface Drug {
  id: number;
  drugCode: string;
  drugName: string;
  atcCode: string | null;
  _count?: {
    salesDaily: number;
    forecastsDaily: number;
  };
}

interface DrugTableProps {
  drugs: Drug[];
}

export default function DrugTable({ drugs }: DrugTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
              Drug Code
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
              Drug Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
              ATC Code
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
              Sales Records
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
              Forecasts
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {drugs.map((drug) => (
            <tr key={drug.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {drug.drugCode}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                {drug.drugName}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                {drug.atcCode || '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                {drug._count?.salesDaily || 0}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                {drug._count?.forecastsDaily || 0}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <a
                  href={`/drugs/${drug.id}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  View Details →
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
