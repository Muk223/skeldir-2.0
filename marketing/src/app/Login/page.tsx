import { LoginPage } from '@/components/auth/login/LoginPage';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Login - Skeldir',
    description: 'Login to your Skeldir account.',
};

export default function Page() {
    return <LoginPage />;
}
