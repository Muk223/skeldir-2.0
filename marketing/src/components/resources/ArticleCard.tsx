"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { ArticleMetadata } from "@/data/articlesData";

interface ArticleCardProps {
    article: ArticleMetadata;
}

const categoryColors: Record<string, { bg: string; text: string }> = {
    'Attribution': { bg: '#3B82F6', text: '#FFFFFF' },
    'Budget Planning': { bg: '#10B981', text: '#FFFFFF' },
};

export function ArticleCard({ article }: ArticleCardProps) {
    const router = useRouter();
    
    const handleClick = () => {
        router.push(`/resources/${article.slug}`);
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    };

    const categoryStyle = categoryColors[article.category] || categoryColors['Attribution'];

    return (
        <article
            onClick={handleClick}
            className="group relative flex flex-col bg-white rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 ease-out"
            style={{
                border: '1px solid #E5E7EB',
            }}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleClick();
                }
            }}
            onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.1)';
                e.currentTarget.style.borderColor = '#3B82F6';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = '#E5E7EB';
            }}
            onMouseDown={(e) => {
                e.currentTarget.style.transform = 'scale(0.98)';
            }}
            onMouseUp={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
            }}
        >
            {/* Image Container */}
            <div className="relative w-full" style={{ aspectRatio: '16/9' }}>
                <Image
                    src={article.heroImagePath}
                    alt={article.heroImageAlt}
                    fill
                    className="object-cover"
                    sizes="(max-width: 767px) 100vw, (max-width: 1023px) 50vw, 33vw"
                    loading="lazy"
                />
                {/* Category Badge */}
                <div
                    className="absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-semibold"
                    style={{
                        backgroundColor: categoryStyle.bg,
                        color: categoryStyle.text,
                    }}
                >
                    {article.category}
                </div>
            </div>

            {/* Content */}
            <div className="flex flex-col flex-grow p-6">
                {/* Title */}
                <h3
                    className="font-semibold line-clamp-2 mb-2"
                    style={{
                        fontSize: '20px',
                        lineHeight: '1.3',
                        color: '#111827',
                    }}
                >
                    {article.title}
                </h3>

                {/* Author & Read Time */}
                <p
                    className="mb-3"
                    style={{
                        fontSize: '14px',
                        fontWeight: 400,
                        color: '#6B7280',
                    }}
                >
                    By {article.author || 'Julie Atli'} • {article.readTimeMinutes} min
                </p>

                {/* Excerpt */}
                <p
                    className="line-clamp-3 mb-4 flex-grow"
                    style={{
                        fontSize: '15px',
                        lineHeight: '1.6',
                        color: '#4B5563',
                    }}
                >
                    {article.excerpt}
                </p>

                {/* Date */}
                <p
                    style={{
                        fontSize: '13px',
                        color: '#9CA3AF',
                    }}
                >
                    {formatDate(article.publishDate)}
                </p>
            </div>
        </article>
    );
}
