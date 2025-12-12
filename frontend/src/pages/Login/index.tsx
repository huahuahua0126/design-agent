import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, message, Tabs, Select } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { authApi } from '../../services/api'
import { useAuthStore } from '../../stores/authStore'
import './index.css'

export default function Login() {
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('login')
    const navigate = useNavigate()
    const { login } = useAuthStore()

    const handleLogin = async (values: { username: string; password: string }) => {
        setLoading(true)
        try {
            const { data } = await authApi.login(values.username, values.password)
            login(data.access_token, data.user)
            message.success('登录成功')
            navigate('/')
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } }
            message.error(err.response?.data?.detail || '登录失败')
        } finally {
            setLoading(false)
        }
    }

    const handleRegister = async (values: {
        username: string
        email: string
        password: string
        full_name: string
        role: string
    }) => {
        setLoading(true)
        try {
            await authApi.register(values)
            message.success('注册成功，请登录')
            setActiveTab('login')
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } }
            message.error(err.response?.data?.detail || '注册失败')
        } finally {
            setLoading(false)
        }
    }

    const tabItems = [
        {
            key: 'login',
            label: '登录',
            children: (
                <Form onFinish={handleLogin} size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                        <Input prefix={<UserOutlined />} placeholder="用户名" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                        <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item>
                        <Button type="primary" htmlType="submit" block loading={loading}>
                            登录
                        </Button>
                    </Form.Item>
                </Form>
            ),
        },
        {
            key: 'register',
            label: '注册',
            children: (
                <Form onFinish={handleRegister} size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                        <Input prefix={<UserOutlined />} placeholder="用户名" />
                    </Form.Item>
                    <Form.Item
                        name="email"
                        rules={[
                            { required: true, message: '请输入邮箱' },
                            { type: 'email', message: '请输入有效的邮箱' },
                        ]}
                    >
                        <Input prefix={<MailOutlined />} placeholder="邮箱" />
                    </Form.Item>
                    <Form.Item name="full_name">
                        <Input prefix={<UserOutlined />} placeholder="姓名 (可选)" />
                    </Form.Item>
                    <Form.Item name="role" initialValue="operator" rules={[{ required: true }]}>
                        <Select placeholder="选择角色">
                            <Select.Option value="operator">运营</Select.Option>
                            <Select.Option value="designer">设计师</Select.Option>
                        </Select>
                    </Form.Item>
                    <Form.Item
                        name="password"
                        rules={[
                            { required: true, message: '请输入密码' },
                            { min: 6, message: '密码至少6位' },
                        ]}
                    >
                        <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item>
                        <Button type="primary" htmlType="submit" block loading={loading}>
                            注册
                        </Button>
                    </Form.Item>
                </Form>
            ),
        },
    ]

    return (
        <div className="login-container">
            <Card className="login-card">
                <h1 className="login-title">设计需求 Agent 系统</h1>
                <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} centered />
            </Card>
        </div>
    )
}
