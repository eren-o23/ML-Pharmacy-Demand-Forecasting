import { prisma } from '@/lib/db';
import DrugTable from '@/components/DrugTable';

async function getDrugs() {
  const drugs = await prisma.drug.findMany({
    orderBy: {
      drugCode: 'asc',
    },
    include: {
      _count: {
        select: {
          salesDaily: true,
          forecastsDaily: true,
        },
      },
    },
  });

  return drugs;
}

export default async function DrugsPage() {
  const drugs = await getDrugs();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Drugs</h1>
        <p className="text-gray-600">
          Browse all drugs in the system with their sales and forecast data
        </p>
      </div>

      {drugs.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800 font-medium">No drugs found</p>
          <p className="text-yellow-700 text-sm mt-2">
            Run the ML pipeline to load and process drug data
          </p>
        </div>
      ) : (
        <>
          <div className="bg-white p-4 rounded-lg shadow">
            <p className="text-sm text-gray-600">
              Showing <span className="font-semibold">{drugs.length}</span> drugs
            </p>
          </div>
          <DrugTable drugs={drugs} />
        </>
      )}
    </div>
  );
}
