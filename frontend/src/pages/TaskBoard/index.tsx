import { useState, useEffect } from 'react'
import { Card, Row, Col, Tag, Button, Modal, message, Empty } from 'antd'
import { PlayCircleOutlined, CheckCircleOutlined, EditOutlined, FileDoneOutlined } from '@ant-design/icons'
import { requirementsApi, tasksApi } from '../../services/api'
import { useAuthStore } from '../../stores/authStore'
import './index.css'

interface Requirement {
    id: number
    title: string
    requirement_type: string
    dimensions: string
    status: string
    created_at: string
    designer_id: number
    requester_id: number
}

const statusConfig: Record<string, { label: string; color: string }> = {
    pending: { label: '待接单', color: 'default' },
    in_progress: { label: '进行中', color: 'processing' },
    under_review: { label: '待验收', color: 'warning' },
    revising: { label: '修改中', color: 'error' },
    completed: { label: '已完成', color: 'success' },
}

const columns = ['pending', 'in_progress', 'under_review', 'revising', 'completed']

export default function TaskBoard() {
    const [requirements, setRequirements] = useState<Requirement[]>([])
    const [loading, setLoading] = useState(true)
    const { user } = useAuthStore()

    useEffect(() => {
        loadRequirements()
    }, [])

    const loadRequirements = async () => {
        try {
            const { data } = await requirementsApi.list({ limit: 100 })
            setRequirements(data)
        } catch (error) {
            message.error('加载失败')
        } finally {
            setLoading(false)
        }
    }

    const handleAction = async (id: number, action: string) => {
        try {
            switch (action) {
                case 'start':
                    await tasksApi.start(id)
                    message.success('已开始制作')
                    break
                case 'submit':
                    await tasksApi.submitReview(id)
                    message.success('已提交验收')
                    break
                case 'revision':
                    await tasksApi.requestRevision(id)
                    message.success('已发起修改')
                    break
                case 'complete':
                    await tasksApi.complete(id)
                    message.success('任务已完成')
                    break
            }
            loadRequirements()
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } }
            message.error(err.response?.data?.detail || '操作失败')
        }
    }

    const renderCard = (req: Requirement) => {
        const isDesigner = user?.role === 'designer'
        const isOperator = user?.role === 'operator'

        return (
            <Card key={req.id} size="small" className="task-card">
                <div className="task-title">{req.title}</div>
                <div className="task-meta">
                    <Tag>{req.requirement_type}</Tag>
                    {req.dimensions && <span>{req.dimensions}</span>}
                </div>
                <div className="task-actions">
                    {req.status === 'pending' && isDesigner && (
                        <Button
                            type="primary"
                            size="small"
                            icon={<PlayCircleOutlined />}
                            onClick={() => handleAction(req.id, 'start')}
                        >
                            开始制作
                        </Button>
                    )}
                    {(req.status === 'in_progress' || req.status === 'revising') && isDesigner && (
                        <Button
                            type="primary"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={() => handleAction(req.id, 'submit')}
                        >
                            提交验收
                        </Button>
                    )}
                    {req.status === 'under_review' && isOperator && (
                        <>
                            <Button
                                size="small"
                                icon={<EditOutlined />}
                                onClick={() => handleAction(req.id, 'revision')}
                            >
                                需要修改
                            </Button>
                            <Button
                                type="primary"
                                size="small"
                                icon={<FileDoneOutlined />}
                                onClick={() => handleAction(req.id, 'complete')}
                            >
                                确认完成
                            </Button>
                        </>
                    )}
                </div>
            </Card>
        )
    }

    return (
        <div className="task-board">
            <Row gutter={16}>
                {columns.map((status) => (
                    <Col key={status} className="board-column">
                        <div className="column-header">
                            <Tag color={statusConfig[status].color}>{statusConfig[status].label}</Tag>
                            <span className="count">
                                {requirements.filter((r) => r.status === status).length}
                            </span>
                        </div>
                        <div className="column-content">
                            {requirements.filter((r) => r.status === status).length === 0 ? (
                                <Empty description="暂无任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                            ) : (
                                requirements.filter((r) => r.status === status).map(renderCard)
                            )}
                        </div>
                    </Col>
                ))}
            </Row>
        </div>
    )
}
