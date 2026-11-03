import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

interface Props {
  onlineCount: number;
  offlineCount: number;
  totalCount: number;
}

export default function AgentAvailabilityChart({ onlineCount, offlineCount, totalCount }: Props) {
  const data = [
    { name: 'Online', value: onlineCount, color: '#4ade80' },
    { name: 'Offline', value: offlineCount, color: '#34404f' },
  ];

  return (
    <div className="health-content">
      <div className="donut-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              innerRadius={66}
              outerRadius={86}
              paddingAngle={4}
              stroke="none"
            >
              {data.map((item) => (
                <Cell key={item.name} fill={item.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: '#151b24',
                border: '1px solid #293341',
                borderRadius: 8,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <strong>{totalCount}</strong>
          <span>AGENTS</span>
        </div>
      </div>
      <div className="health-legend">
        <div>
          <i className="legend-dot online-dot" />
          <span>Online</span>
          <strong>{onlineCount}</strong>
        </div>
        <div>
          <i className="legend-dot offline-dot" />
          <span>Offline</span>
          <strong>{offlineCount}</strong>
        </div>
        <div className="health-summary">
          <span>Fleet availability</span>
          <strong>{totalCount ? `${Math.round((onlineCount / totalCount) * 100)}%` : '—'}</strong>
        </div>
      </div>
    </div>
  );
}
