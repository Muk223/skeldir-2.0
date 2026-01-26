"use client";

import { ArticleMetadata } from "@/data/articlesData";
import { ArticleCard } from "./ArticleCard";

interface ArticleGridProps {
    articles: ArticleMetadata[];
}

export function ArticleGrid({ articles }: ArticleGridProps) {
    if (articles.length === 0) {
        return (
            <div className="text-center py-12">
                <p
                    style={{
                        fontSize: '16px',
                        color: '#6B7280',
                    }}
                >
                    No articles found in this category.
                </p>
            </div>
        );
    }

    return (
        <section className="w-full pb-16 md:pb-20 lg:pb-24">
            <div className="container mx-auto px-4 md:px-6">
                <div
                    className="grid gap-6 md:gap-8"
                    style={{
                        gridTemplateColumns: 'repeat(1, 1fr)',
                    }}
                >
                    {/* Responsive grid using CSS */}
                    <style jsx>{`
            @media (min-width: 768px) {
              div.grid {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 24px 24px !important;
              }
            }
            @media (min-width: 1024px) {
              div.grid {
                grid-template-columns: repeat(3, 1fr) !important;
                gap: 32px 24px !important;
              }
            }
          `}</style>
                    {articles.map((article) => (
                        <ArticleCard key={article.id} article={article} />
                    ))}
                </div>
            </div>
        </section>
    );
}
