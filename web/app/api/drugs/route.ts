import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET() {
  try {
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

    return NextResponse.json(drugs);
  } catch (error) {
    console.error('Error fetching drugs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch drugs' },
      { status: 500 }
    );
  }
}
