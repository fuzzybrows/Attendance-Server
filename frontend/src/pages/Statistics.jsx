import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchStats, fetchMemberStats } from '../store/statsSlice';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#10b981', '#ef4444', '#6366f1', '#f59e0b'];

const Statistics = () => {
    const dispatch = useDispatch();
    const { overall, memberDetail } = useSelector(state => state.stats);
    const [selectedMember, setSelectedMember] = useState(null);

    useEffect(() => {
        dispatch(fetchStats());
    }, [dispatch]);

    const handleMemberLookup = (memberId) => {
        setSelectedMember(memberId);
        dispatch(fetchMemberStats(memberId));
    };

    const overallData = overall.map(m => ({
        name: m.name.split(' ')[0],
        prompt: m.prompt_count,
        late: m.late_count
    })).slice(0, 10); // Show top 10 for chart

    const promptnessRank = [...overall].sort((a, b) => b.prompt_rate - a.prompt_rate);

    return (
        <div className="container">
            <header>
                <h1>Attendance Insights</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Performance and promptness analysis.</p>
            </header>

            <div className="grid">
                {/* Overall Performance Chart */}
                <div className="glass-card">
                    <h2>Promptness Overview (Top 10)</h2>
                    <div style={{ height: '300px', width: '100%' }}>
                        <ResponsiveContainer>
                            <BarChart data={overallData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="name" stroke="var(--text-secondary)" />
                                <YAxis stroke="var(--text-secondary)" />
                                <Tooltip
                                    contentStyle={{ background: 'var(--card-bg)', border: '1px solid rgba(255,255,255,0.1)' }}
                                    itemStyle={{ color: 'white' }}
                                />
                                <Bar dataKey="prompt" fill="#10b981" name="Prompt" stackId="a" />
                                <Bar dataKey="late" fill="#ef4444" name="Late" stackId="a" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Promptness Ranking */}
                <div className="glass-card">
                    <h2>Promptness Ranking</h2>
                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        <table>
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Member</th>
                                    <th>Rate</th>
                                </tr>
                            </thead>
                            <tbody>
                                {promptnessRank.map((m, index) => (
                                    <tr key={m.member_id} style={{ cursor: 'pointer' }} onClick={() => handleMemberLookup(m.member_id)}>
                                        <td>#{index + 1}</td>
                                        <td>{m.name}</td>
                                        <td>
                                            <span style={{ color: m.prompt_rate > 80 ? '#10b981' : m.prompt_rate > 50 ? '#f59e0b' : '#ef4444' }}>
                                                {m.prompt_rate}%
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Member Details Lookup */}
            {memberDetail && (
                <div className="glass-card" style={{ marginTop: '2rem' }}>
                    <h2>Member Deep-Dive: {memberDetail.member_name}</h2>
                    <div className="grid">
                        <div style={{ height: '200px' }}>
                            <ResponsiveContainer>
                                <PieChart>
                                    <Pie
                                        data={[
                                            { name: 'Prompt', value: memberDetail.history.filter(h => h.status === 'prompt').length },
                                            { name: 'Late', value: memberDetail.history.filter(h => h.status === 'late').length }
                                        ]}
                                        innerRadius={60}
                                        outerRadius={80}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        <Cell fill="#10b981" />
                                        <Cell fill="#ef4444" />
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div>
                            <h3>Recent History</h3>
                            <ul style={{ listStyle: 'none', padding: 0 }}>
                                {memberDetail.history.slice(0, 5).map((h, i) => (
                                    <li key={i} style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                                        <span>{h.session_title}</span>
                                        <span className={`status-badge status-${h.status === 'prompt' ? 'manual' : 'nfc'}`} style={{ background: h.status === 'prompt' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: h.status === 'prompt' ? '#10b981' : '#ef4444' }}>
                                            {h.status}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Statistics;
