import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Typography } from 'antd'
import {
    MessageOutlined,
    ProjectOutlined,
    BarChartOutlined,
    LogoutOutlined,
    UserOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../stores/authStore'

const { Header, Content } = Layout
const { Title } = Typography

const menuItems = [
    {
        key: '/requirements',
        icon: <MessageOutlined />,
        label: '需求采集',
    },
    {
        key: '/tasks',
        icon: <ProjectOutlined />,
        label: '任务看板',
    },
    {
        key: '/reports',
        icon: <BarChartOutlined />,
        label: '统计报表',
    },
]

export default function MainLayout() {
    const navigate = useNavigate()
    const location = useLocation()
    const { user, logout } = useAuthStore()

    const handleMenuClick = ({ key }: { key: string }) => {
        navigate(key)
    }

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    const dropdownItems = [
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '退出登录',
            onClick: handleLogout,
        },
    ]

    return (
        <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
            <Header
                style={{
                    background: '#fff',
                    padding: '0 24px',
                    display: 'flex',
                    alignItems: 'center',
                    boxShadow: '0 1px 4px rgba(0, 0, 0, 0.08)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 100,
                }}
            >
                <Title level={4} style={{ color: '#333', margin: 0, marginRight: 48 }}>
                    设计需求 Agent
                </Title>
                <Menu
                    mode="horizontal"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={handleMenuClick}
                    style={{
                        flex: 1,
                        border: 'none',
                        background: 'transparent',
                    }}
                />
                <Dropdown menu={{ items: dropdownItems }} placement="bottomRight">
                    <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Avatar
                            icon={<UserOutlined />}
                            style={{ background: '#666' }}
                        />
                        <span style={{ color: '#333' }}>{user?.full_name || user?.username}</span>
                    </div>
                </Dropdown>
            </Header>
            <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
                <Outlet />
            </Content>
        </Layout>
    )
}
