import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import type { AiChatMessage } from "@shared/schema";

const quickQuestions = [
  "What are common drug interactions with aspirin?",
  "What is the recommended dosage for amoxicillin in adults?",
  "What are the side effects of metformin?",
  "How should insulin be stored?",
  "What are the symptoms of an allergic reaction?",
];

export default function AIAssistant() {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const { data: messages, isLoading } = useQuery<AiChatMessage[]>({
    queryKey: ["/api/ai/messages", sessionId],
    enabled: !!sessionId,
  });

  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      apiRequest("POST", "/api/ai/chat", {
        message,
        sessionId: sessionId || undefined,
      }),
    onSuccess: (data) => {
      if (!sessionId && data.sessionId) {
        setSessionId(data.sessionId);
      }
      queryClient.invalidateQueries({
        queryKey: ["/api/ai/messages", data.sessionId],
      });
      setMessage("");
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!message.trim()) return;
    sendMutation.mutate(message);
  };

  const handleQuickQuestion = (question: string) => {
    setMessage(question);
    sendMutation.mutate(question);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold" data-testid="title-ai-assistant">
          AI Drug Information Assistant
        </h1>
        <p className="text-sm text-muted-foreground">
          Ask questions about medications, dosages, interactions, and more
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Chat with AI Assistant
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col p-0">
              <ScrollArea
                className="flex-1 p-4"
                ref={scrollRef}
                data-testid="chat-messages"
              >
                {!sessionId || !messages || messages.length === 0 ? (
                  <div className="text-center text-muted-foreground py-12">
                    <Bot className="mx-auto h-12 w-12 mb-4" />
                    <p>Start a conversation by asking a question below</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
                        data-testid={`message-${msg.id}`}
                      >
                        {msg.role === "assistant" && (
                          <div className="flex-shrink-0">
                            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                              <Bot className="h-4 w-4 text-primary-foreground" />
                            </div>
                          </div>
                        )}
                        <div
                          className={`max-w-[80%] rounded-lg p-3 ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted"
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">
                            {msg.content}
                          </p>
                        </div>
                        {msg.role === "user" && (
                          <div className="flex-shrink-0">
                            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center">
                              <User className="h-4 w-4 text-secondary-foreground" />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    {sendMutation.isPending && (
                      <div className="flex gap-3">
                        <div className="flex-shrink-0">
                          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                            <Bot className="h-4 w-4 text-primary-foreground" />
                          </div>
                        </div>
                        <div className="bg-muted rounded-lg p-3">
                          <Loader2 className="h-4 w-4 animate-spin" />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </ScrollArea>

              <div className="p-4 border-t">
                <div className="flex gap-2">
                  <Input
                    placeholder="Ask about drugs, dosages, interactions..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    disabled={sendMutation.isPending}
                    data-testid="input-message"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={!message.trim() || sendMutation.isPending}
                    data-testid="button-send"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Questions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {quickQuestions.map((question, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="cursor-pointer hover-elevate active-elevate-2 w-full justify-start text-left p-3 h-auto whitespace-normal"
                  onClick={() => handleQuickQuestion(question)}
                  data-testid={`quick-question-${index}`}
                >
                  {question}
                </Badge>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">About AI Assistant</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                This AI assistant is powered by advanced language models and can
                help you with:
              </p>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>Drug information and usage</li>
                <li>Dosage recommendations</li>
                <li>Drug interactions</li>
                <li>Side effects and contraindications</li>
                <li>Medical conditions and treatments</li>
              </ul>
              <p className="text-xs pt-2">
                Note: Always verify critical medical information with
                professional sources.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
