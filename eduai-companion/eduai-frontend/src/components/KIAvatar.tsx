import React from "react";

const PERSONA_STYLES: Record<string, { farbe: string; emoji: string }> = {
    mentor:    { farbe: "#6366f1", emoji: "\uD83E\uDDD9\u200D\u2642\uFE0F" },
    buddy:     { farbe: "#06b6d4", emoji: "\uD83E\uDD19" },
    pruefer:   { farbe: "#f59e0b", emoji: "\uD83D\uDCCB" },
    motivator: { farbe: "#22c55e", emoji: "\uD83D\uDE80" },
    sokrates:  { farbe: "#8b5cf6", emoji: "\uD83C\uDFDB\uFE0F" },
};

interface KIAvatarProps {
    persona: string;
    isTyping: boolean;
}

const KIAvatar: React.FC<KIAvatarProps> = ({ persona, isTyping }) => {
    const style = PERSONA_STYLES[persona] || PERSONA_STYLES.mentor;

    return (
        <div
            className={`relative flex items-center justify-center w-10 h-10 rounded-xl
                        transition-all duration-300
                        ${isTyping ? "animate-pulse-glow scale-110" : ""}`}
            style={{ background: `${style.farbe}22`, border: `2px solid ${style.farbe}66` }}
        >
            <span className="text-lg">{style.emoji}</span>

            {isTyping && (
                <>
                    <div
                        className="absolute inset-0 rounded-xl animate-ping opacity-30"
                        style={{ background: style.farbe }}
                    />
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 flex gap-0.5">
                        {[0, 1, 2].map(i => (
                            <div
                                key={i}
                                className="w-1 h-1 rounded-full animate-bounce"
                                style={{
                                    background: style.farbe,
                                    animationDelay: `${i * 0.15}s`
                                }}
                            />
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default KIAvatar;
