'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts';

interface ForecastData {
  date: string;
  predicted?: number;
  lowerCi?: number;
  upperCi?: number;
  actual?: number;
}

interface ForecastChartProps {
  data: ForecastData[];
  title?: string;
}

export default function ForecastChart({ data, title }: ForecastChartProps) {
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          
          {/* Confidence interval area */}
          {data.some(d => d.lowerCi !== undefined) && (
            <Area
              type="monotone"
              dataKey="lowerCi"
              stackId="1"
              stroke="none"
              fill="#93c5fd"
              fillOpacity={0.3}
              name="Lower CI"
            />
          )}
          {data.some(d => d.upperCi !== undefined) && (
            <Area
              type="monotone"
              dataKey="upperCi"
              stackId="1"
              stroke="none"
              fill="#93c5fd"
              fillOpacity={0.3}
              name="Upper CI"
            />
          )}
          
          {/* Actual sales */}
          {data.some(d => d.actual !== undefined) && (
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Actual Sales"
            />
          )}
          
          {/* Predicted demand */}
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="Predicted Demand"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
