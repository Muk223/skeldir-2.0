"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArticleMetadata } from "@/data/articlesData";

interface ResourcesHeroProps {
    article: ArticleMetadata;
}

export function ResourcesHero({ article }: ResourcesHeroProps) {
    const router = useRouter();
    
    const handleClick = () => {
        router.push(`/resources/${article.slug}`);
    };

    return (
        <section className="w-full pt-4 md:pt-6 lg:pt-8 pb-16 md:pb-20 lg:pb-24">
            <div className="container mx-auto px-4 md:px-6">
                <article
                    onClick={handleClick}
                    className="group relative grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 bg-white rounded-3xl overflow-hidden cursor-pointer transition-all duration-300"
                    role="link"
                    tabIndex={0}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleClick();
                        }
                    }}
                    style={{
                        border: '1px solid #E5E7EB',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.boxShadow = '0 20px 40px -10px rgba(0, 0, 0, 0.12)';
                        e.currentTarget.style.borderColor = '#3B82F6';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.boxShadow = 'none';
                        e.currentTarget.style.borderColor = '#E5E7EB';
                    }}
                >
                    {/* Image Section */}
                    <div 
                        className="relative w-full order-1 lg:order-1 overflow-hidden" 
                        style={{ 
                            aspectRatio: '16/9',
                        }}
                    >
                        <Image
                            src={article.heroImagePath}
                            alt={article.heroImageAlt}
                            fill
                            className="object-cover"
                            sizes="(max-width: 1023px) 100vw, 50vw"
                            priority
                        />
                        {/* Gradient overlays for smooth edge blending to white container */}
                        {/* Right edge fade (most important - where it meets white content) */}
                        <div
                            className="absolute top-0 right-0 bottom-0 pointer-events-none z-10"
                            style={{
                                width: '120px',
                                background: 'linear-gradient(to left, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.7) 30%, rgba(255, 255, 255, 0.3) 60%, transparent 100%)',
                            }}
                        />
                        {/* Top edge fade */}
                        <div
                            className="absolute top-0 left-0 right-0 pointer-events-none z-10"
                            style={{
                                height: '80px',
                                background: 'linear-gradient(to bottom, rgba(255, 255, 255, 0.5) 0%, rgba(255, 255, 255, 0.2) 50%, transparent 100%)',
                            }}
                        />
                        {/* Bottom edge fade */}
                        <div
                            className="absolute bottom-0 left-0 right-0 pointer-events-none z-10"
                            style={{
                                height: '120px',
                                background: 'linear-gradient(to top, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.7) 30%, rgba(255, 255, 255, 0.3) 60%, transparent 100%)',
                            }}
                        />
                        {/* Left edge fade */}
                        <div
                            className="absolute top-0 left-0 bottom-0 pointer-events-none z-10"
                            style={{
                                width: '60px',
                                background: 'linear-gradient(to right, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.15) 50%, transparent 100%)',
                            }}
                        />
                    </div>

                    {/* Content Section */}
                    <div className="flex flex-col justify-center p-6 md:p-8 lg:p-12 order-2 lg:order-2">
                        {/* Category Badge */}
                        <div className="mb-4">
                            <span
                                className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold"
                                style={{
                                    backgroundColor: '#3B82F6',
                                    color: '#FFFFFF',
                                }}
                            >
                                {article.category}
                            </span>
                        </div>

                        {/* Title */}
                        <h1
                            className="font-semibold mb-3"
                            style={{
                                fontSize: 'clamp(32px, 5vw, 48px)',
                                lineHeight: '1.1',
                                color: '#111827',
                            }}
                        >
                            {article.title}
                        </h1>

                        {/* Subtitle */}
                        <h2
                            className="mb-4"
                            style={{
                                fontSize: 'clamp(18px, 3vw, 24px)',
                                fontWeight: 400,
                                lineHeight: '1.3',
                                color: '#4B5563',
                            }}
                        >
                            {article.subtitle}
                        </h2>

                        {/* Author & Read Time */}
                        <div className="flex items-center gap-3 mb-6">
                            <div>
                                <p
                                    style={{
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        color: '#374151',
                                    }}
                                >
                                    Amulya Puri
                                </p>
                                <p
                                    style={{
                                        fontSize: '13px',
                                        color: '#6B7280',
                                    }}
                                >
                                    {article.readTimeMinutes} min read
                                </p>
                            </div>
                        </div>

                        {/* Excerpt */}
                        <p
                            className="mb-8"
                            style={{
                                fontSize: '16px',
                                lineHeight: '1.7',
                                color: '#4B5563',
                            }}
                        >
                            {article.excerpt}
                        </p>

                        {/* CTA Button */}
                        <div>
                            <Link href={`/resources/${article.slug}`}>
                                <Button
                                    className="transition-all"
                                    style={{
                                        backgroundColor: '#2563EB',
                                        color: '#FFFFFF',
                                        fontFamily: 'Inter, sans-serif',
                                        fontSize: '15px',
                                        fontWeight: 600,
                                        padding: '12px 28px',
                                        height: 'auto',
                                        borderRadius: '8px',
                                        boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.backgroundColor = '#1E40AF';
                                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.4)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.backgroundColor = '#2563EB';
                                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(37, 99, 235, 0.25)';
                                    }}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                    }}
                                >
                                    Read article
                                </Button>
                            </Link>
                        </div>
                    </div>
                </article>
            </div>
        </section>
    );
}
