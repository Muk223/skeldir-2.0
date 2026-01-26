import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Resources | Skeldir – Marketing Attribution Insights",
    description:
        "Learn how to navigate attribution discrepancies, understand ROAS ranges, and defend budget shifts with evidence-based frameworks from Skeldir.",
    openGraph: {
        title: "Resources | Skeldir – Marketing Attribution Insights",
        description:
            "Learn how to navigate attribution discrepancies, understand ROAS ranges, and defend budget shifts with evidence-based frameworks from Skeldir.",
        url: "https://skeldir.com/resources",
        siteName: "Skeldir",
        images: [
            {
                url: "/images/resources/article-1-hero.png",
                width: 1200,
                height: 675,
                alt: "Skeldir Resources - Attribution Insights",
            },
        ],
        locale: "en_US",
        type: "website",
    },
    twitter: {
        card: "summary_large_image",
        title: "Resources | Skeldir – Marketing Attribution Insights",
        description:
            "Learn how to navigate attribution discrepancies, understand ROAS ranges, and defend budget shifts with evidence-based frameworks from Skeldir.",
        images: ["/images/resources/article-1-hero.png"],
    },
    alternates: {
        canonical: "https://skeldir.com/resources",
    },
};

export default function ResourcesLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
