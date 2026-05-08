import { ReactNode } from 'react'
import { AdminRoute } from './AdminRoute'
import { AdminNav, AdminNavItem } from './AdminNav'

interface AdminLayoutProps {
  children: ReactNode
  // Builder fills these in when stamping the template — one nav item per
  // generated Manage<Entity> page.
  navItems: AdminNavItem[]
  publicHomePath?: string
}

// AdminLayout is the wrapper every admin route renders inside. Use it once
// at the top of the /admin/* route subtree, e.g. in App.tsx:
//
//   <Route path="/admin/*" element={
//     <AdminLayout navItems={ADMIN_NAV_ITEMS}>
//       <Routes>
//         <Route path="services" element={<ManageServices />} />
//         ...
//       </Routes>
//     </AdminLayout>
//   } />
export function AdminLayout({ children, navItems, publicHomePath }: AdminLayoutProps) {
  return (
    <AdminRoute>
      <div className="min-h-screen bg-gray-50">
        <AdminNav items={navItems} publicHomePath={publicHomePath} />
        {children}
      </div>
    </AdminRoute>
  )
}
