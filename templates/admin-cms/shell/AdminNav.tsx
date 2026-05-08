import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LogOut, Home, Settings as SettingsIcon, LayoutDashboard } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { useToast } from '@/hooks/use-toast'

// Icon imports for nav items live in the generated `admin-nav-items.ts`,
// which imports from lucide-react and constructs the `items` array passed in.

export interface AdminNavItem {
  path: string
  label: string
  // Icon is a lucide-react component reference. Builder fills these in based
  // on detected content types (e.g. MapPin for locations, Users for team).
  Icon: React.ComponentType<{ className?: string }>
}

interface AdminNavProps {
  // Builder generates this list when stamping the template into a client site.
  // Order = display order in the nav bar.
  items: AdminNavItem[]
  // Path users click "Back to Site" to return to (default "/").
  publicHomePath?: string
}

export function AdminNav({ items, publicHomePath = '/' }: AdminNavProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { toast } = useToast()

  const isActive = (path: string) => location.pathname === path

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    navigate(publicHomePath)
    toast({
      title: 'Signed out',
      description: 'You have been signed out successfully',
    })
  }

  return (
    <div className="bg-white border-b mb-8">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Left side - Navigation links */}
          <div className="flex items-center gap-1 overflow-x-auto">
            {items.length === 0 && (
              <Button variant="ghost" disabled className="gap-2">
                <LayoutDashboard className="h-4 w-4" />
                Admin
              </Button>
            )}
            {items.map(({ path, label, Icon }) => (
              <Button
                key={path}
                variant={isActive(path) ? 'default' : 'ghost'}
                onClick={() => navigate(path)}
                className="gap-2"
              >
                <Icon className="h-4 w-4" />
                {label}
              </Button>
            ))}
            <Button
              variant={isActive('/admin/settings') ? 'default' : 'ghost'}
              onClick={() => navigate('/admin/settings')}
              className="gap-2"
            >
              <SettingsIcon className="h-4 w-4" />
              Settings
            </Button>
          </div>

          {/* Right side - Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => navigate(publicHomePath)}
              className="gap-2"
              size="sm"
            >
              <Home className="h-4 w-4" />
              Back to Site
            </Button>
            <Button
              variant="ghost"
              onClick={handleSignOut}
              className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
              size="sm"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
