import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const drugId = searchParams.get('drugId');
    const from = searchParams.get('from');
    const to = searchParams.get('to');

    if (!drugId) {
      return NextResponse.json(
        { error: 'drugId parameter is required' },
        { status: 400 }
      );
    }

    const where: any = {
      drugId: parseInt(drugId),
    };

    if (from) {
      where.forecastDate = {
        ...where.forecastDate,
        gte: new Date(from),
      };
    }

    if (to) {
      where.forecastDate = {
        ...where.forecastDate,
        lte: new Date(to),
      };
    }

    // Get latest run timestamp
    const latestRun = await prisma.forecastDaily.findFirst({
      where: { drugId: parseInt(drugId) },
      orderBy: { runTimestamp: 'desc' },
      select: { runTimestamp: true },
    });

    if (!latestRun) {
      return NextResponse.json([]);
    }

    // Get forecasts from latest run
    const forecasts = await prisma.forecastDaily.findMany({
      where: {
        ...where,
        runTimestamp: latestRun.runTimestamp,
      },
      orderBy: {
        forecastDate: 'asc',
      },
      include: {
        drug: {
          select: {
            drugCode: true,
            drugName: true,
          },
        },
      },
    });

    return NextResponse.json(forecasts);
  } catch (error) {
    console.error('Error fetching forecasts:', error);
    return NextResponse.json(
      { error: 'Failed to fetch forecasts' },
      { status: 500 }
    );
  }
}
