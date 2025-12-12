import { useState } from 'react'
import { Card, DatePicker, Button, Table, message, Statistic, Row, Col } from 'antd'
import { DownloadOutlined, BarChartOutlined, ClockCircleOutlined, CheckCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { reportsApi } from '../../services/api'
import './index.css'

const { RangePicker } = DatePicker

interface DesignerStats {
    designer_id: number
    designer_name: string
    total_tasks: number
    completed_tasks: number
    total_hours: number
    avg_hours_per_task: number
}

export default function Reports() {
    const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
        dayjs().startOf('month'),
        dayjs().endOf('month'),
    ])
    const [stats, setStats] = useState<DesignerStats[]>([])
    const [loading, setLoading] = useState(false)

    const handleQuery = async () => {
        if (!dateRange[0] || !dateRange[1]) {
            message.error('请选择日期范围')
            return
        }

        setLoading(true)
        try {
            const { data } = await reportsApi.getDesignerStats(
                dateRange[0].format('YYYY-MM-DD'),
                dateRange[1].format('YYYY-MM-DD')
            )
            setStats(data)
        } catch (error) {
            message.error('查询失败')
        } finally {
            setLoading(false)
        }
    }

    const handleExport = async () => {
        if (!dateRange[0] || !dateRange[1]) {
            message.error('请选择日期范围')
            return
        }

        try {
            const response = await reportsApi.exportExcel(
                dateRange[0].format('YYYY-MM-DD'),
                dateRange[1].format('YYYY-MM-DD')
            )

            // 下载文件
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', `设计师统计_${dateRange[0].format('YYYY-MM-DD')}_${dateRange[1].format('YYYY-MM-DD')}.xlsx`)
            document.body.appendChild(link)
            link.click()
            link.remove()

            message.success('导出成功')
        } catch (error) {
            message.error('导出失败')
        }
    }

    const columns = [
        { title: '设计师', dataIndex: 'designer_name', key: 'designer_name' },
        { title: '总任务数', dataIndex: 'total_tasks', key: 'total_tasks' },
        { title: '已完成', dataIndex: 'completed_tasks', key: 'completed_tasks' },
        { title: '总工时(小时)', dataIndex: 'total_hours', key: 'total_hours' },
        { title: '平均工时', dataIndex: 'avg_hours_per_task', key: 'avg_hours_per_task' },
    ]

    // 汇总统计
    const totalTasks = stats.reduce((sum, s) => sum + s.total_tasks, 0)
    const totalCompleted = stats.reduce((sum, s) => sum + s.completed_tasks, 0)
    const totalHours = stats.reduce((sum, s) => sum + s.total_hours, 0)

    return (
        <div className="reports-page">
            <Card title="📊 效能统计报表" className="filter-card">
                <div className="filter-row">
                    <span>日期范围：</span>
                    <RangePicker
                        value={dateRange}
                        onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
                        presets={[
                            { label: '本月', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
                            { label: '上月', value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
                            { label: '本季度', value: [dayjs().startOf('quarter'), dayjs().endOf('quarter')] },
                        ]}
                    />
                    <Button type="primary" onClick={handleQuery} loading={loading}>
                        查询
                    </Button>
                    <Button icon={<DownloadOutlined />} onClick={handleExport}>
                        导出 Excel
                    </Button>
                </div>
            </Card>

            {stats.length > 0 && (
                <>
                    <Row gutter={16} className="stats-row">
                        <Col span={8}>
                            <Card>
                                <Statistic
                                    title="总任务数"
                                    value={totalTasks}
                                    prefix={<BarChartOutlined />}
                                />
                            </Card>
                        </Col>
                        <Col span={8}>
                            <Card>
                                <Statistic
                                    title="已完成"
                                    value={totalCompleted}
                                    prefix={<CheckCircleOutlined />}
                                    valueStyle={{ color: '#52c41a' }}
                                />
                            </Card>
                        </Col>
                        <Col span={8}>
                            <Card>
                                <Statistic
                                    title="总工时(小时)"
                                    value={totalHours.toFixed(1)}
                                    prefix={<ClockCircleOutlined />}
                                />
                            </Card>
                        </Col>
                    </Row>

                    <Card title="设计师明细" className="table-card">
                        <Table
                            columns={columns}
                            dataSource={stats}
                            rowKey="designer_id"
                            pagination={false}
                        />
                    </Card>
                </>
            )}
        </div>
    )
}
