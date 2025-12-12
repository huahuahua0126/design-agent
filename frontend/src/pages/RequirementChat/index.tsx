import { useState, useEffect, useRef, useCallback } from 'react'
import { Card, Row, Col, Input, Button, List, Avatar, Form, Select, DatePicker, message, Spin, Tag, Upload, Image } from 'antd'
import { SendOutlined, PictureOutlined, RobotOutlined, UserOutlined, CheckCircleOutlined } from '@ant-design/icons'
import type { UploadFile, UploadProps } from 'antd'
import { requirementsApi, adminApi } from '../../services/api'
import { useAuthStore } from '../../stores/authStore'
import './index.css'

interface Message {
    role: 'user' | 'assistant'
    content: string
    images?: string[]
}

interface RequirementForm {
    title: string
    requirement_type: string
    dimensions: string
    deadline: string
    copywriting: string
    designer_id: number | null
    reference_images: string[]
}

const defaultForm: RequirementForm = {
    title: '',
    requirement_type: '',
    dimensions: '',
    deadline: '',
    copywriting: '',
    designer_id: null,
    reference_images: [],
}

export default function RequirementChat() {
    const [messages, setMessages] = useState<Message[]>([])
    const [inputValue, setInputValue] = useState('')
    const [loading, setLoading] = useState(false)
    const [connecting, setConnecting] = useState(true)
    const [requirementForm, setRequirementForm] = useState<RequirementForm>(defaultForm)
    const [missingFields, setMissingFields] = useState<string[]>(['title', 'requirement_type', 'dimensions'])
    const [isComplete, setIsComplete] = useState(false)
    const [designSpecs, setDesignSpecs] = useState<string[]>([])
    const [designers, setDesigners] = useState<{ id: number; full_name: string }[]>([])
    const [conversationId, setConversationId] = useState<string>('')
    const [fileList, setFileList] = useState<UploadFile[]>([])
    const [previewOpen, setPreviewOpen] = useState(false)
    const [previewImage, setPreviewImage] = useState('')

    const wsRef = useRef<WebSocket | null>(null)
    const { token } = useAuthStore()
    const conversationIdRef = useRef<string>('')
    const isInitialized = useRef(false)  // 标志：是否已从 localStorage 恢复完成

    // 从 localStorage 恢复状态（只在组件首次挂载时执行一次）
    useEffect(() => {
        const savedMessages = localStorage.getItem('requirement_chat_messages')
        const savedForm = localStorage.getItem('requirement_chat_form')
        const savedConversationId = localStorage.getItem('requirement_chat_conversation_id')
        const savedMissingFields = localStorage.getItem('requirement_chat_missing_fields')
        const savedDesignSpecs = localStorage.getItem('requirement_chat_design_specs')
        const savedIsComplete = localStorage.getItem('requirement_chat_is_complete')

        if (savedMessages) {
            try {
                const parsed = JSON.parse(savedMessages)
                if (Array.isArray(parsed) && parsed.length > 0) {
                    setMessages(parsed)
                }
            } catch (e) { /* ignore */ }
        }
        if (savedForm) {
            try {
                const parsed = JSON.parse(savedForm)
                if (parsed && parsed.title) {  // 只有有内容才恢复
                    setRequirementForm(parsed)
                }
            } catch (e) { /* ignore */ }
        }
        if (savedConversationId) {
            setConversationId(savedConversationId)
            conversationIdRef.current = savedConversationId
        }
        if (savedMissingFields) {
            try {
                setMissingFields(JSON.parse(savedMissingFields))
            } catch (e) { /* ignore */ }
        }
        if (savedDesignSpecs) {
            try {
                setDesignSpecs(JSON.parse(savedDesignSpecs))
            } catch (e) { /* ignore */ }
        }
        if (savedIsComplete === 'true') {
            setIsComplete(true)
        }

        // 标记初始化完成
        isInitialized.current = true
    }, [])

    // 保存状态到 localStorage（只在初始化完成后才保存）
    useEffect(() => {
        if (!isInitialized.current) return  // 初始化未完成，不保存
        localStorage.setItem('requirement_chat_messages', JSON.stringify(messages))
    }, [messages])

    useEffect(() => {
        if (!isInitialized.current) return
        localStorage.setItem('requirement_chat_form', JSON.stringify(requirementForm))
    }, [requirementForm])

    // 自动根据表单内容更新 missingFields 和 isComplete
    useEffect(() => {
        const missing: string[] = []
        if (!requirementForm.title) missing.push('title')
        if (!requirementForm.requirement_type) missing.push('requirement_type')
        if (!requirementForm.dimensions) missing.push('dimensions')

        setMissingFields(missing)
        setIsComplete(missing.length === 0)
    }, [requirementForm.title, requirementForm.requirement_type, requirementForm.dimensions])

    useEffect(() => {
        if (!isInitialized.current) return
        if (conversationId) {
            localStorage.setItem('requirement_chat_conversation_id', conversationId)
        }
    }, [conversationId])

    useEffect(() => {
        if (!isInitialized.current) return
        localStorage.setItem('requirement_chat_missing_fields', JSON.stringify(missingFields))
    }, [missingFields])

    useEffect(() => {
        if (!isInitialized.current) return
        localStorage.setItem('requirement_chat_design_specs', JSON.stringify(designSpecs))
    }, [designSpecs])

    useEffect(() => {
        if (!isInitialized.current) return
        localStorage.setItem('requirement_chat_is_complete', String(isComplete))
    }, [isComplete])

    // WebSocket 连接
    const connectWebSocket = useCallback(() => {
        if (!token) return

        // 使用代理路径
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${wsProtocol}//${window.location.host}/api/agent/ws/${token}`
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            console.log('WebSocket connected')
            setConnecting(false)
            // 发送 init 消息
            ws.send(JSON.stringify({
                type: 'init',
                conversation_id: conversationIdRef.current || null
            }))
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            if (data.type === 'message') {
                setMessages(prev => [...prev, { role: 'assistant', content: data.response }])

                // 更新表单
                if (data.updated_form) {
                    setRequirementForm(prev => ({
                        ...prev,
                        ...data.updated_form,
                        designer_id: prev.designer_id,
                        reference_images: prev.reference_images,
                    }))
                }

                // 更新状态
                setMissingFields(data.missing_fields || [])
                setIsComplete(data.is_complete || false)
                setDesignSpecs(data.design_specs || [])
                if (data.conversation_id) {
                    setConversationId(data.conversation_id)
                    conversationIdRef.current = data.conversation_id
                }
                setLoading(false)
            } else if (data.type === 'connected') {
                // 重连成功，不显示消息
                if (data.conversation_id) {
                    conversationIdRef.current = data.conversation_id
                }
            }
        }

        ws.onclose = () => {
            console.log('WebSocket disconnected')
            setConnecting(true)
            setTimeout(connectWebSocket, 5000) // 延长重连时间
        }

        ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            setConnecting(true)
        }

        wsRef.current = ws
    }, [token])

    useEffect(() => {
        loadDesigners()
        connectWebSocket()

        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [connectWebSocket])

    const loadDesigners = async () => {
        try {
            const { data } = await adminApi.getDesigners()
            setDesigners(data)

            const myDesigner = await adminApi.getMyDesigner()
            if (myDesigner.data.designer_id) {
                setRequirementForm(prev => ({ ...prev, designer_id: myDesigner.data.designer_id }))
            }
        } catch (error) {
            console.error('Failed to load designers:', error)
        }
    }

    const handleSend = async () => {
        if (!inputValue.trim() || loading) return
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            message.error('连接已断开，正在重连...')
            connectWebSocket()
            return
        }

        const userMessage = inputValue.trim()
        setInputValue('')
        setMessages(prev => [...prev, { role: 'user', content: userMessage }])
        setLoading(true)

        wsRef.current.send(JSON.stringify({
            message: userMessage,
            current_form: requirementForm,
            conversation_id: conversationId
        }))
    }

    const handleSubmit = async () => {
        if (!requirementForm.title) {
            message.error('请填写需求标题')
            return
        }
        if (!requirementForm.designer_id) {
            message.error('请选择设计师')
            return
        }

        try {
            await requirementsApi.create({
                title: requirementForm.title,
                requirement_type: requirementForm.requirement_type || 'other',
                dimensions: requirementForm.dimensions,
                copywriting: requirementForm.copywriting,
                designer_id: requirementForm.designer_id,
                reference_images: requirementForm.reference_images,
            })
            message.success('需求提交成功！')
            setRequirementForm({ ...defaultForm, designer_id: requirementForm.designer_id })
            setMessages([])
            setFileList([])
            setIsComplete(false)
            setMissingFields(['title', 'requirement_type', 'dimensions'])
            setDesignSpecs([])
            // 清空 localStorage
            localStorage.removeItem('requirement_chat_messages')
            localStorage.removeItem('requirement_chat_form')
            localStorage.removeItem('requirement_chat_conversation_id')
            localStorage.removeItem('requirement_chat_missing_fields')
            localStorage.removeItem('requirement_chat_design_specs')
            localStorage.removeItem('requirement_chat_is_complete')

            if (wsRef.current) {
                wsRef.current.close()
            }
            connectWebSocket()
        } catch (error) {
            message.error('提交失败，请重试')
        }
    }

    // 图片上传配置
    const uploadProps: UploadProps = {
        listType: 'picture',
        fileList,
        showUploadList: false,
        beforeUpload: (file) => {
            const isImage = file.type.startsWith('image/')
            if (!isImage) {
                message.error('只能上传图片文件!')
                return Upload.LIST_IGNORE
            }
            const isLt5M = file.size / 1024 / 1024 < 5
            if (!isLt5M) {
                message.error('图片大小不能超过 5MB!')
                return Upload.LIST_IGNORE
            }
            return false // 阻止自动上传
        },
        onChange: async ({ fileList: newFileList }) => {
            // 为每个新文件生成预览 URL
            const processedList = await Promise.all(
                newFileList.map(async (file) => {
                    if (file.originFileObj && !file.thumbUrl) {
                        try {
                            const base64 = await getBase64(file.originFileObj)
                            return { ...file, thumbUrl: base64, url: base64 }
                        } catch {
                            return file
                        }
                    }
                    return file
                })
            )
            setFileList(processedList)

            // 更新表单中的参考图
            const images = processedList
                .filter(f => f.thumbUrl)
                .map(f => f.thumbUrl as string)
            setRequirementForm(prev => ({ ...prev, reference_images: images }))
        },
        onPreview: async (file) => {
            const previewUrl = file.thumbUrl || file.url
            if (previewUrl) {
                setPreviewImage(previewUrl)
                setPreviewOpen(true)
            }
        },
        onRemove: (file) => {
            const newList = fileList.filter(f => f.uid !== file.uid)
            setFileList(newList)
            const images = newList
                .filter(f => f.thumbUrl)
                .map(f => f.thumbUrl as string)
            setRequirementForm(prev => ({ ...prev, reference_images: images }))
        },
    }

    const getBase64 = (file: File): Promise<string> =>
        new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.readAsDataURL(file)
            reader.onload = () => resolve(reader.result as string)
            reader.onerror = (error) => reject(error)
        })

    const fieldLabels: Record<string, string> = {
        title: '标题',
        requirement_type: '类型',
        dimensions: '尺寸',
        deadline: '截止时间',
        copywriting: '文案'
    }

    return (
        <Row gutter={24} className="requirement-chat">
            {/* 左侧对话区 */}
            <Col span={14}>
                <Card
                    title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <RobotOutlined />
                            <span>AI 需求助手</span>
                            {connecting && <Tag color="orange">连接中...</Tag>}
                            {!connecting && <Tag color="green">已连接</Tag>}
                        </div>
                    }
                    className="chat-card"
                >
                    <div className="message-list">
                        {connecting && messages.length === 0 && (
                            <div style={{ textAlign: 'center', padding: 40 }}>
                                <Spin tip="正在连接 AI 助手..." />
                            </div>
                        )}
                        <List
                            dataSource={messages}
                            renderItem={(msg) => (
                                <List.Item className={`message-item ${msg.role}`}>
                                    <List.Item.Meta
                                        avatar={
                                            <Avatar
                                                icon={msg.role === 'assistant' ? <RobotOutlined /> : <UserOutlined />}
                                                style={{ background: msg.role === 'assistant' ? '#666' : '#333' }}
                                            />
                                        }
                                        description={<div className="message-content">{msg.content}</div>}
                                    />
                                </List.Item>
                            )}
                        />
                        {loading && (
                            <div style={{ textAlign: 'center', padding: 16 }}>
                                <Spin tip="AI 正在思考..." />
                            </div>
                        )}
                    </div>

                    {/* 设计规范建议 */}
                    {designSpecs.length > 0 && (
                        <div className="design-specs">
                            <div className="specs-title">📋 设计规范建议</div>
                            {designSpecs.map((spec, i) => (
                                <div key={i} className="spec-item">{spec}</div>
                            ))}
                        </div>
                    )}

                    <div className="input-area">
                        <Input.TextArea
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="描述您的设计需求..."
                            autoSize={{ minRows: 2, maxRows: 4 }}
                            disabled={connecting}
                            onPressEnter={(e) => {
                                if (!e.shiftKey) {
                                    e.preventDefault()
                                    handleSend()
                                }
                            }}
                        />
                        <div className="input-actions">
                            <Upload {...uploadProps}>
                                <Button icon={<PictureOutlined />} disabled={connecting} size="large">
                                    上传参考图 {fileList.length > 0 ? `(${fileList.length}张)` : ''}
                                </Button>
                            </Upload>
                            <Button
                                type="primary"
                                icon={<SendOutlined />}
                                loading={loading}
                                onClick={handleSend}
                                disabled={connecting}
                                style={{ background: '#333' }}
                            >
                                发送
                            </Button>
                        </div>
                    </div>
                </Card>
            </Col>

            {/* 右侧需求单 */}
            <Col span={10}>
                <Card
                    title={
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>📋 需求单</span>
                            {isComplete && <Tag icon={<CheckCircleOutlined />} color="success">信息完整</Tag>}
                        </div>
                    }
                    className="form-card"
                >
                    {/* 缺失字段提示 */}
                    {missingFields.length > 0 && (
                        <div className="missing-fields">
                            待补充：{missingFields.map(f => fieldLabels[f] || f).join('、')}
                        </div>
                    )}

                    <Form layout="vertical">
                        <Form.Item label="需求标题" required>
                            <Input
                                value={requirementForm.title}
                                onChange={(e) => setRequirementForm({ ...requirementForm, title: e.target.value })}
                                placeholder="如：双十一促销 Banner"
                                status={missingFields.includes('title') ? 'warning' : ''}
                            />
                        </Form.Item>
                        <Form.Item label="设计类型" required>
                            <Select
                                value={requirementForm.requirement_type || undefined}
                                onChange={(v) => setRequirementForm({ ...requirementForm, requirement_type: v })}
                                placeholder="选择类型"
                                status={missingFields.includes('requirement_type') ? 'warning' : ''}
                            >
                                <Select.Option value="banner">Banner</Select.Option>
                                <Select.Option value="poster">海报</Select.Option>
                                <Select.Option value="detail_page">详情页</Select.Option>
                                <Select.Option value="icon">图标</Select.Option>
                                <Select.Option value="other">其他</Select.Option>
                            </Select>
                        </Form.Item>
                        <Form.Item label="尺寸" required>
                            <Input
                                value={requirementForm.dimensions}
                                onChange={(e) => setRequirementForm({ ...requirementForm, dimensions: e.target.value })}
                                placeholder="如：1080x640"
                                status={missingFields.includes('dimensions') ? 'warning' : ''}
                            />
                        </Form.Item>
                        <Form.Item label="文案内容">
                            <Input.TextArea
                                value={requirementForm.copywriting}
                                onChange={(e) => setRequirementForm({ ...requirementForm, copywriting: e.target.value })}
                                rows={3}
                                placeholder="需要放在设计上的文字"
                            />
                        </Form.Item>
                        <Form.Item label="参考图">
                            {fileList.length > 0 ? (
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                    {fileList.map((file, index) => (
                                        <Image
                                            key={index}
                                            width={60}
                                            height={60}
                                            src={file.thumbUrl || file.url}
                                            style={{ objectFit: 'cover', borderRadius: 4 }}
                                        />
                                    ))}
                                </div>
                            ) : (
                                <span style={{ color: '#999' }}>暂无参考图</span>
                            )}
                        </Form.Item>
                        <Form.Item label="交付时间">
                            <DatePicker
                                style={{ width: '100%' }}
                                showTime
                                onChange={(_, dateString) =>
                                    setRequirementForm({ ...requirementForm, deadline: dateString as string })
                                }
                            />
                        </Form.Item>
                        <Form.Item label="指派设计师" required>
                            <Select
                                value={requirementForm.designer_id || undefined}
                                onChange={(v) => setRequirementForm({ ...requirementForm, designer_id: v })}
                                placeholder="选择设计师"
                            >
                                {designers.map((d) => (
                                    <Select.Option key={d.id} value={d.id}>
                                        {d.full_name}
                                    </Select.Option>
                                ))}
                            </Select>
                        </Form.Item>
                        <Form.Item>
                            <Button
                                type="primary"
                                block
                                size="large"
                                onClick={handleSubmit}
                                disabled={!isComplete && missingFields.length > 0}
                                style={{ background: '#333', color: '#fff' }}
                            >
                                提交需求
                            </Button>
                        </Form.Item>
                    </Form>
                </Card>
            </Col>

            {/* 图片预览 */}
            <Image
                style={{ display: 'none' }}
                preview={{
                    visible: previewOpen,
                    src: previewImage,
                    onVisibleChange: (value) => setPreviewOpen(value),
                }}
            />
        </Row >
    )
}
